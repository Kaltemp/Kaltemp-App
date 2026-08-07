import os
from dotenv import load_dotenv

RUTA_ENV = r'C:\kaltemp_app\kaltemp-backend-fastapi-v2\.env'

print('¿Existe el archivo?', os.path.exists(RUTA_ENV))
load_dotenv(RUTA_ENV)

for nombre in ['BSALE_TOKEN', 'BSALE_ACCESS_TOKEN']:
    valor = os.getenv(nombre)
    print(f'{nombre}: encontrado={valor is not None}, longitud={len(valor) if valor else 0}')