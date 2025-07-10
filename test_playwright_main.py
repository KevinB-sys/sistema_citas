from playwright.sync_api import sync_playwright

def test_login_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("http://localhost:5000/login")
        page.fill("#email", "usuario@ejemplo.com")
        page.fill("#password", "password123")
        page.click("button[type='submit']")
        # Esperar por el título de bienvenida en vez de la URL
        page.wait_for_selector("h1:has-text('Bienvenido')", timeout=15000)
        assert page.is_visible("h1:has-text('Bienvenido')")
        print("✅ Login Playwright exitoso")
        browser.close()

def test_registro_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("http://localhost:5000/register")
        page.fill("#nombre", "Usuario Ejemplo")
        page.fill("#email", "usuario12@ejemplo.com")
        page.fill("#password", "password123")
        page.fill("#telefono", "0999999999")
        page.click("button[type='submit']")
        # Esperar por el título de bienvenida en vez de la URL
        page.wait_for_selector("h1:has-text('Bienvenido')", timeout=15000)
        assert page.is_visible("h1:has-text('Bienvenido')")
        print("✅ Registro Playwright exitoso")
        browser.close()

def test_agendar_cita_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        # Login
        page.goto("http://localhost:5000/login")
        page.fill("#email", "usuario@ejemplo.com")
        page.fill("#password", "password123")
        page.click("button[type='submit']")
        page.wait_for_selector("h1:has-text('Bienvenido')", timeout=15000)
        # Ir a Agendar Cita
        page.click("text=Agendar Cita")
        page.wait_for_url("**/agendar-cita")

        # Seleccionar especialidad
        page.select_option("#especialidad", label="Cardiología")

        # Esperar a que el select de médicos tenga una opción válida (distinta al placeholder)
        page.wait_for_function("""
            () => {
                const sel = document.querySelector('#medico');
                return sel && sel.options.length > 1 && sel.options[1].value !== '';
            }
        """)
        # Seleccionar el primer médico disponible
        page.select_option("#medico", index=1)

        # Seleccionar fecha (ajusta la fecha si es necesario)
        page.fill("#fecha", "2025-12-31")

        # Esperar a que el select de horarios tenga una opción válida
        page.wait_for_function("""
            () => {
                const sel = document.querySelector('#horario');
                return sel && sel.options.length > 1 && sel.options[1].value !== '';
            }
        """)
        # Seleccionar el primer horario disponible
        page.select_option("#horario", index=1)

        # Enviar el formulario
        page.click("button[type='submit']")

        # Verificar éxito
        page.wait_for_selector(".alert-success")
        assert page.is_visible(".alert-success")
        print("✅ Cita agendada con Playwright")

        browser.close()
        
        
def test_buscar_medicos_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Modo headless
        page = browser.new_page()
        
        # Login
        page.goto("http://localhost:5000/login")
        page.fill("#email", "usuario@ejemplo.com")
        page.fill("#password", "password123")
        page.click("button[type='submit']")
        
        # Buscar médicos
        page.click("text=Buscar Médicos")
        page.select_option("#especialidad_id", label="Dermatología")
        page.click("button[type='submit']")
        
        # Verificar resultados
        assert page.is_visible(".card-title")
        print("✅ Búsqueda de médicos exitosa (Headless)")
        
        browser.close()

def test_cancelar_cita_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("http://localhost:5000/login")
        page.fill("#email", "usuario@ejemplo.com")
        page.fill("#password", "password123")
        page.click("button[type='submit']")
        page.wait_for_selector("h1:has-text('Bienvenido')", timeout=15000)
        page.click("text=Mis Citas")
        # Esperar a que se cargue la tabla/lista de citas
        page.wait_for_selector("button:has-text('Cancelar')", timeout=10000)
        with page.expect_dialog() as dialog_info:
            page.click("button:has-text('Cancelar')")
        dialog_info.value.accept()
        page.wait_for_selector(".alert-success", timeout=10000)
        assert page.is_visible(".alert-success")
        print("✅ Cancelación de cita Playwright exitosa")
        browser.close()