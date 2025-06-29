from playwright.async_api import async_playwright
import asyncio

async def consultar_nfe(chave_acesso: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("🔗 Acessando página da SEFAZ...")
        await page.goto("https://www.nfe.fazenda.gov.br/portal/consultaRecaptcha.aspx?tipoConsulta=resumo&tipoConteudo=7PhJ+gAVw2g%3D")

        print("✍️ Preenchendo a chave da nota...")
        await page.fill('input[name="ctl00$ContentPlaceHolder1$txtChaveAcessoResumo"]', chave_acesso)

        print("\n🤖 Por favor, resolva o captcha manualmente na janela do navegador.")
        print("   NÃO clique em 'Continuar'. Apenas resolva o captcha.")
        input("\n⏳ Pressione ENTER aqui quando terminar de resolver o captcha...")

        print("🚀 Clicando em Continuar...")
        await page.click('#ctl00$ContentPlaceHolder1$btnConsultarHCaptcha')

        print("⏳ Aguardando carregamento dos dados da NFe...")
        try:
            await page.wait_for_selector('#ctl00_ContentPlaceHolder1_lblRazaoEmitente', timeout=30000)
        except:
            try:
                erro_element = await page.locator('span[id*="erro"], div[class*="erro"], .alert-danger').first.text_content()
                if erro_element:
                    await browser.close()
                    raise Exception(f"Erro na consulta: {erro_element}")
            except:
                pass
            await browser.close()
            raise Exception("Timeout ao aguardar dados da NFe. Verifique se a chave está correta.")

        emitente = await page.locator('#ctl00_ContentPlaceHolder1_lblRazaoEmitente').inner_text()
        cnpj = await page.locator('#ctl00_ContentPlaceHolder1_lblCNPJEmitente').inner_text()
        valor_total = await page.locator('#ctl00_ContentPlaceHolder1_lblValorNota').inner_text()
        data_emissao = await page.locator('#ctl00_ContentPlaceHolder1_lblEmissao').inner_text()

        print("\n✅ Dados extraídos com sucesso:")
        print(f"Emitente: {emitente}")
        print(f"CNPJ: {cnpj}")
        print(f"Data de Emissão: {data_emissao}")
        print(f"Valor Total: {valor_total}")

        await browser.close()
        
        return {
            "emitente": emitente,
            "cnpj_emitente": cnpj,
            "valor_total": valor_total,
            "data_emissao": data_emissao
        }

if __name__ == "__main__":
    import asyncio
    chave = input("🔑 Digite a chave de acesso da NF-e: ").strip()
    asyncio.run(consultar_nfe(chave))