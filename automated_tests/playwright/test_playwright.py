from playwright.sync_api import sync_playwright

def test_login_playwright():
    with sync_playwright() as p:
        # Configuración del navegador
        browser = p.chromium.launch(headless=False)  # headless=True para modo sin interfaz
        page = browser.new_page()
        
        try:
            # 1. Abrir login
            page.goto("http://localhost:5000/login")
            
            # 2. Rellenar credenciales
            page.fill("#email", "usuario@ejemplo.com")
            page.fill("#password", "password123")
            
            # 3. Enviar formulario
            page.click("button[type='submit']")
            
            # 4. Esperar dashboard
            page.wait_for_url("**/dashboard")
            
            # 5. Verificar mensaje de bienvenida
            assert page.is_visible("h1:has-text('Bienvenido')")
            
            print("✅ Prueba de login con Playwright exitosa")
            
        finally:
            browser.close()

test_login_playwright()