import requests
from typing import List, Dict, Optional
from datetime import datetime, time
import logging

class EmployeesService:
    def __init__(self, nest_api_base_url: str = "http://localhost:3000"):
        self.base_url = nest_api_base_url
        self.employees_endpoint = f"{self.base_url}/employees"
        
    def get_all_doctors(self) -> List[Dict]:
        """Obtener todos los empleados (doctores) del sistema NestJS"""
        try:
            response = requests.get(self.employees_endpoint, timeout=10)
            response.raise_for_status()
            
            employees = response.json()
            # Filtrar solo los que tienen especialidad (son doctores)
            doctors = [emp for emp in employees if emp.get('especialidad')]
            return doctors
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al obtener doctores de NestJS: {e}")
            return []
    
    def get_doctor_by_id(self, doctor_id: str) -> Optional[Dict]:
        """Obtener un doctor específico por ID"""
        try:
            doctors = self.get_all_doctors()
            return next((doc for doc in doctors if doc['id'] == doctor_id), None)
        except Exception as e:
            logging.error(f"Error al obtener doctor {doctor_id}: {e}")
            return None
    
    def get_doctors_by_specialty(self, especialidad: str) -> List[Dict]:
        """Obtener doctores por especialidad"""
        try:
            doctors = self.get_all_doctors()
            return [doc for doc in doctors if doc.get('especialidad', '').lower() == especialidad.lower()]
        except Exception as e:
            logging.error(f"Error al obtener doctores por especialidad {especialidad}: {e}")
            return []
    
    def is_doctor_active(self, doctor_id: str) -> bool:
        """Verificar si un doctor está activo"""
        doctor = self.get_doctor_by_id(doctor_id)
        return doctor.get('activo', False) if doctor else False
    
    def sync_doctor_with_local_db(self, db, doctor_data: Dict) -> Optional[object]:
        """Sincronizar datos del doctor con la base de datos local si es necesario"""
        # Esta función puede ser útil si quieres mantener una copia local
        # para mejorar el rendimiento
        pass
