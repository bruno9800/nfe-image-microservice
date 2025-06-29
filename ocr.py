from PIL import Image
import pytesseract
import re
import io
from pdf2image import convert_from_bytes

# Adicionar suporte para HEIC
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    print("HEIC support enabled")
except ImportError:
    print("HEIC support not available - pillow-heif not installed")
    pass  # Se não tiver pillow-heif instalado, continua sem suporte HEIC

def extrair_chave_e_cnpj(file_bytes: bytes, is_pdf: bool = False) -> dict:
    # Processa baseado no tipo já validado
    if is_pdf:
        # Para PDF, pega apenas a primeira página
        imagens = convert_from_bytes(file_bytes, dpi=300, first_page=1, last_page=1)
        img = imagens[0]
    else:
        # Para imagens (PNG, JPG, HEIC, etc.)
        try:
            img = Image.open(io.BytesIO(file_bytes))
            
            # Converte HEIC/HEIF para PNG em memória antes do OCR
            if img.format in ['HEIF', 'HEIC']:
                print(f"Converting {img.format} to PNG for OCR processing")
                # Converte para RGB se necessário
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Salva como PNG em memória
                png_buffer = io.BytesIO()
                img.save(png_buffer, format='PNG')
                png_buffer.seek(0)
                
                # Recarrega como PNG
                img = Image.open(png_buffer)
            else:
                # Para outros formatos, apenas converte para RGB se necessário
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
        except Exception as e:
            return {
                "error": f"Erro ao processar imagem: {str(e)}. Verifique se o formato é suportado.",
                "chave_acesso": None,
                "cnpj_destinatario": None,
                "cpf_destinatario": None
            }
    
    # Configurações otimizadas do OCR para NFe
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz./-: '
    
    # Extrai texto da imagem com configuração otimizada
    try:
        texto = pytesseract.image_to_string(img, lang='eng', config=custom_config)
    except Exception as e:
        return {
            "error": f"Erro no OCR: {str(e)}",
            "chave_acesso": None,
            "cnpj_destinatario": None,
            "cpf_destinatario": None
        }
    
    # Remove espaços da chave para busca
    texto_limpo = texto.replace(" ", "").replace("\n", "")

    # 1. CHAVE DE ACESSO (44 dígitos) - busca mais robusta
    chave = None
    
    # Busca por "Chave de acesso" seguido dos números
    chave_pattern = r'(?:Chave\s*de\s*acesso|chave\s*de\s*acesso)[^\d]*([\d\s]{44,60})'
    chave_match = re.search(chave_pattern, texto, re.IGNORECASE)
    if chave_match:
        chave_raw = re.sub(r'\D', '', chave_match.group(1))
        if len(chave_raw) == 44:
            chave = chave_raw
    
    # Se não encontrou, busca por sequência de 44 dígitos
    if not chave:
        chaves = re.findall(r'\d{44}', texto_limpo)
        chave = chaves[0] if chaves else None
    
    # Se ainda não encontrou, busca por padrão com espaços
    if not chave:
        chave_espacos = re.search(r'(\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4})', texto)
        if chave_espacos:
            chave = re.sub(r'\D', '', chave_espacos.group(1))

    # 2. BUSCA CNPJ/CPF DO DESTINATÁRIO
    cnpj_destinatario = None
    cpf_destinatario = None
    
    # Divide o texto em linhas para análise contextual
    linhas = texto.split('\n')
    
    # Busca pela seção DESTINATÁRIO/REMETENTE
    for i, linha in enumerate(linhas):
        linha_upper = linha.upper()
        
        # Identifica seção do destinatário
        if any(palavra in linha_upper for palavra in ['DESTINATÁRIO', 'DESTINATARIO', 'DEST']):
            # Procura nas próximas 10 linhas
            for j in range(i, min(i + 10, len(linhas))):
                linha_busca = linhas[j]
                
                # Busca CNPJ (formato: XX.XXX.XXX/XXXX-XX)
                cnpj_match = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', linha_busca)
                if cnpj_match and not cnpj_destinatario:
                    cnpj_destinatario = cnpj_match.group(1).replace('.', '').replace('/', '').replace('-', '')
                
                # Busca CPF (formato: XXX.XXX.XXX-XX)
                cpf_match = re.search(r'(\d{3}\.\d{3}\.\d{3}-\d{2})', linha_busca)
                if cpf_match and not cpf_destinatario:
                    cpf_destinatario = cpf_match.group(1).replace('.', '').replace('-', '')
                
                # Se encontrou ambos ou chegou em outra seção, para
                if (cnpj_destinatario or cpf_destinatario) and any(palavra in linha_busca.upper() for palavra in ['EMITENTE', 'PRODUTO', 'FATURA', 'CÁLCULO']):
                    break
    
    # 3. BUSCA ALTERNATIVA - se não encontrou na seção específica
    if not cnpj_destinatario and not cpf_destinatario:
        # Busca todos os CNPJs e CPFs no documento
        cnpjs_encontrados = re.findall(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', texto)
        cpfs_encontrados = re.findall(r'\d{3}\.\d{3}\.\d{3}-\d{2}', texto)
        
        # Pega o primeiro que não seja do emitente (geralmente o segundo encontrado)
        if len(cnpjs_encontrados) > 1:
            cnpj_destinatario = cnpjs_encontrados[1].replace('.', '').replace('/', '').replace('-', '')
        elif len(cnpjs_encontrados) == 1:
            cnpj_destinatario = cnpjs_encontrados[0].replace('.', '').replace('/', '').replace('-', '')
            
        if len(cpfs_encontrados) > 0:
            cpf_destinatario = cpfs_encontrados[0].replace('.', '').replace('-', '')

    return {
        "chave_acesso": chave,
        "cnpj_destinatario": cnpj_destinatario,
        "cpf_destinatario": cpf_destinatario
    }