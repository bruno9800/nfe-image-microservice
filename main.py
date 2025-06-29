from fastapi import FastAPI, File, UploadFile
from ocr import extrair_chave_e_cnpj

app = FastAPI()

@app.post("/extract-info")
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