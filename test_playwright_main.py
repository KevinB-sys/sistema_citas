from playwright.sync_api import sync_playwright

def test_agendar_cita_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Login
        page.goto("http://localhost:5000/login")
        page.fill("#email", "paciente@test.com")
        page.fill("#password", "password123")
        page.click("button[type='submit']")
        
        # Agendar cita
        page.click("text=Agendar Nueva Cita")
        page.select_option("#especialidad", label="Cardiología")
        page.wait_for_selector("#medico option:nth-child(2)")
        page.select_option("#medico", index=1)
        page.fill("#fecha", "2025-12-31")
        page.wait_for_selector("#horario option:nth-child(2)")
        page.select_option("#horario", index=1)
        page.click("button[type='submit']")
        
        # Verificar éxito
        assert page.is_visible(".alert-success")
        print("✅ Cita agendada con Playwright")
        
        browser.close()
        
        
def test_buscar_medicos_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Modo headless
        page = browser.new_page()
        
        # Login
        page.goto("http://localhost:5000/login")
        page.fill("#email", "paciente@test.com")
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