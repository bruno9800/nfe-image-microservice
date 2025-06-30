from fastapi import FastAPI, File, UploadFile
from ocr import extrair_chave_e_cnpj
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, HTTPException, Header
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ou especifique domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}



def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

@app.post("/extract-info", dependencies=[Depends(verify_api_key)])
async def extract_info(file: UploadFile = File(...)):
    content = await file.read()
    
    # Verifica se é um tipo suportado (incluindo HEIC)
    supported_types = (
        'application/pdf', 
        'image/png', 
        'image/jpeg', 
        'image/jpg',
        'image/heic',
        'image/heif'
    )
    
    if file.content_type not in supported_types:
        return {"error": "Tipo de arquivo não suportado. Use PDF, PNG, JPG ou HEIC."}
    
    # Passa apenas se é PDF ou não
    is_pdf = file.content_type == 'application/pdf'
    info = extrair_chave_e_cnpj(content, is_pdf)

    if "error" in info:
        return info
        
    if not info["chave_acesso"]:
        return {"error": "Chave de acesso não encontrada"}

    return info



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)