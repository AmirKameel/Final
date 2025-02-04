from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict
import uuid
import shutil
import os
from datetime import datetime
import xml.etree.ElementTree as ET
import httpx

from exctractv2 import ElementorExtractionAgent
from transformv2 import ContentTransformationAgent
from replacev2 import replace_text_and_colors

class TransformationResponse(BaseModel):
    job_id: str
    status: str
    created_at: str

class JobStatus(BaseModel):
    job_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    output_url: Optional[str] = None
    error: Optional[str] = None

class ThemeTransformer:
    def __init__(self, api_key: str):
        self.extraction_agent = ElementorExtractionAgent()
        self.transformation_agent = ContentTransformationAgent(api_key)
      
        # Create work directories
        self.base_dir = "workdir"
        for dir in ["uploads", "processing", "output"]:
            os.makedirs(os.path.join(self.base_dir, dir), exist_ok=True)
            
        self.jobs: Dict[str, dict] = {}

    def validate_xml(self, file_path: str) -> bool:
        """Validate XML file structure"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            return True
        except ET.ParseError:
            return False

    async def download_xml_from_url(self, url: str, save_path: str):
        """Download XML file from a URL"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                with open(save_path, "wb") as file:
                    file.write(response.content)
            except httpx.RequestError as e:
                raise HTTPException(status_code=400, detail=f"Failed to download XML from URL: {str(e)}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    async def process_theme(self, job_id: str, input_path: str, style_description: str, webhook_url: Optional[str] = None):
        """Process theme transformation asynchronously"""
        work_dir = os.path.join(self.base_dir, "processing", job_id)
        
        try:
            # Update job status
            self.jobs[job_id]["status"] = "processing"
            
            # Create job working directory
            os.makedirs(work_dir, exist_ok=True)
            
            # Validate input XML
            if not self.validate_xml(input_path):
                raise ValueError("Invalid input XML file")
            
            # Extract content
            rag_path = os.path.join(work_dir, "extracted_content.json")
            extraction_result = self.extraction_agent.extract_content(input_path, rag_path)
            
            if not os.path.exists(rag_path):
                raise Exception("Content extraction failed")
            
            # Transform content
            transformed_path = os.path.join(work_dir, "transformed_content.json")
            self.transformation_agent.transform_content(
                rag_path,
                transformed_path,
                style_description
            )
            
            if not os.path.exists(transformed_path):
                raise Exception("Content transformation failed")
            
            # Apply transformations
            output_path = os.path.join(self.base_dir, "output", f"{job_id}.xml")
            replace_text_and_colors(
                input_path,
                transformed_path,
                output_path
            )
            
            # Validate output
            if not self.validate_xml(output_path):
                raise Exception("Output XML validation failed")
                
            # Update job status
            self.jobs[job_id].update({
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "output_url": f"/download/{job_id}"
            })
            
            # Call webhook if provided
            if webhook_url:
                await self._call_webhook(webhook_url, self.jobs[job_id])
                
        except Exception as e:
            self.jobs[job_id].update({
                "status": "failed",
                "completed_at": datetime.utcnow().isoformat(),
                "error": str(e)
            })
            if webhook_url:
                await self._call_webhook(webhook_url, self.jobs[job_id])
            raise
            
        finally:
            # Cleanup processing directory if it exists
            if os.path.exists(work_dir):
                try:
                    shutil.rmtree(work_dir)
                except Exception as e:
                    print(f"Failed to cleanup work directory: {e}")

    async def _call_webhook(self, webhook_url: str, job_data: dict):
        """Call webhook with proper URL validation and error handling"""
        if not webhook_url.startswith(('http://', 'https://')):
            webhook_url = f"https://{webhook_url}"
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    webhook_url, 
                    json=job_data,
                    timeout=10.0
                )
                response.raise_for_status()
            except httpx.RequestError as e:
                print(f"Webhook request failed: {e}")
            except httpx.HTTPStatusError as e:
                print(f"Webhook HTTP error: {e}")
            except Exception as e:
                print(f"Webhook error: {e}")

app = FastAPI(
    title="Elementor Theme Transformer API",
    description="API for transforming WordPress Elementor themes with AI-powered styling",
    version="1.0.0"
)

# Initialize transformer with API key
transformer = ThemeTransformer(api_key=os.getenv("OPENAI_API_KEY"))

@app.post("/transform", response_model=TransformationResponse)
async def transform_theme(
    theme_file: Optional[UploadFile] = File(None),
    theme_url: Optional[str] = Form(None),
    style_description: str = Form(...),
    webhook_url: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Start theme transformation job"""
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    try:
        # Validate input
        if not theme_file and not theme_url:
            raise HTTPException(status_code=400, detail="Either a file or a URL must be provided")
        
        # Save uploaded file or download from URL
        input_path = os.path.join(transformer.base_dir, "uploads", f"{job_id}.xml")
        
        if theme_file:
            if not theme_file.filename.endswith('.xml'):
                raise HTTPException(status_code=400, detail="Only XML files are supported")
                
            try:
                with open(input_path, "wb") as buffer:
                    shutil.copyfileobj(theme_file.file, buffer)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to save file: {str(e)}")
        else:
            await transformer.download_xml_from_url(theme_url, input_path)
        
        # Validate XML structure
        if not transformer.validate_xml(input_path):
            os.remove(input_path)
            raise HTTPException(status_code=400, detail="Invalid XML file structure")
        
        # Create job record
        transformer.jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Start processing in background
        background_tasks.add_task(
            transformer.process_theme,
            job_id,
            input_path,
            style_description,
            webhook_url
        )
        
        return TransformationResponse(**transformer.jobs[job_id])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    if job_id not in transformer.jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = transformer.jobs[job_id]
    print("Job Data:", job_data)  # Debugging: Print job data
    
    try:
        return JobStatus(**job_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid job data structure: {str(e)}")

@app.get("/download/{job_id}")
async def download_transformed_theme(job_id: str):
    """Download transformed theme XML"""
    if job_id not in transformer.jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = transformer.jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
        
    output_path = os.path.join(transformer.base_dir, "output", f"{job_id}.xml")
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Output file not found")
        
    return FileResponse(
        output_path,
        media_type="application/xml",
        filename=f"transformed_theme_{job_id}.xml"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
