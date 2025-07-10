from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_registro_selenium():
    driver = webdriver.Chrome()
    try:
        driver.get("http://localhost:5000/register")
        
        # Rellenar formulario
        driver.find_element(By.ID, "nombre").send_keys("Nuevo Usuario")
        driver.find_element(By.ID, "email").send_keys("nuevo@test.com")
        driver.find_element(By.ID, "password").send_keys("password123")
        driver.find_element(By.ID, "telefono").send_keys("123456789")
        
        # Enviar formulario
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        # Verificar redirección
        WebDriverWait(driver, 10).until(
            EC.url_contains("dashboard")
        )
        print("✅ Registro exitoso con Selenium")
    finally:
        driver.quit()
        
def test_cancelar_cita_selenium():
    driver = webdriver.Chrome()
    try:
        # Login
        driver.get("http://localhost:5000/login")
        driver.find_element(By.ID, "email").send_keys("paciente@test.com")
        driver.find_element(By.ID, "password").send_keys("password123")
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        # Ir a mis citas
        driver.find_element(By.LINK_TEXT, "Mis Citas").click()
        
        # Cancelar primera cita programada
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'Cancelar')]"))
        ).click()
        
        # Verificar mensaje de éxito
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "alert-success"))
        )
        print("✅ Cita cancelada con Selenium")
    finally:
        driver.quit()