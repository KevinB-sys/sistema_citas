from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_login_selenium():
    # Configuración
    driver = webdriver.Chrome()
    
    try:
        # 1. Ir a la página de login
        driver.get("http://localhost:5000/login")
        
        # 2. Rellenar formulario
        email_input = driver.find_element(By.ID, "email")
        email_input.send_keys("usuario@ejemplo.com")
        
        password_input = driver.find_element(By.ID, "password")
        password_input.send_keys("password123")
        
        # 3. Enviar formulario
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        # 4. Verificar redirección al dashboard
        WebDriverWait(driver, 10).until(
            EC.url_contains("dashboard")
        )
        
        # 5. Verificar que se muestra el nombre del usuario
        welcome_message = driver.find_element(By.XPATH, "//h1[contains(text(), 'Bienvenido')]")
        assert "Bienvenido" in welcome_message.text
        
        print("Prueba de login con Selenium exitosa!")
        
    finally:
        driver.quit()

test_login_selenium()