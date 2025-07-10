from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_login_selenium():
    driver = webdriver.Chrome()
    try:
        driver.get("http://localhost:5000/login")
        driver.find_element(By.ID, "email").send_keys("usuario@ejemplo.com")
        driver.find_element(By.ID, "password").send_keys("password123")
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        WebDriverWait(driver, 10).until(
            EC.url_contains("dashboard")
        )
        assert "Bienvenido" in driver.page_source
        print("✅ Login Selenium exitoso")
    finally:
        driver.quit()

def test_registro_selenium():
    driver = webdriver.Chrome()
    try:
        driver.get("http://localhost:5000/register")
        driver.find_element(By.ID, "nombre").send_keys("Usuario Ejemplo")
        driver.find_element(By.ID, "email").send_keys("usuario@ejemplo.com")
        driver.find_element(By.ID, "password").send_keys("password123")
        driver.find_element(By.ID, "telefono").send_keys("0999999999")
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        WebDriverWait(driver, 10).until(
            EC.url_contains("dashboard")
        )
        assert "Bienvenido" in driver.page_source
        print("✅ Registro Selenium exitoso")
    finally:
        driver.quit()

def test_cancelar_cita_selenium():
    driver = webdriver.Chrome()
    try:
        # Login
        driver.get("http://localhost:5000/login")
        driver.find_element(By.ID, "email").send_keys("usuario@ejemplo.com")
        driver.find_element(By.ID, "password").send_keys("password123")
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        WebDriverWait(driver, 10).until(
            EC.url_contains("dashboard")
        )
        # Ir a Mis Citas (espera explícita y selector robusto)
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Mis Citas"))
        ).click()
        # Esperar botón cancelar y cancelar la primera cita
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Cancelar')]"))
        ).click()
        # Verificar mensaje de éxito
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "alert-success"))
        )
        print("✅ Cancelación de cita Selenium exitosa")
    finally:
        driver.quit()