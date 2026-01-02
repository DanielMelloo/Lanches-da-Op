from app import create_app
from database import db
from models import Subsite, get_sp_time
import pytz

app = create_app()
with app.app_context():
    now = get_sp_time()
    print(f"--- DIAGNÓSTICO DE STATUS ---")
    print(f"Horário Atual (SP): {now}")
    print(f"Minutos atuais: {now.hour * 60 + now.minute}")
    print("-" * 30)
    
    subsites = Subsite.query.all()
    for s in subsites:
        print(f"Subsite: {s.name} (ID: {s.id})")
        print(f"  Ativo (Geral): {s.active}")
        print(f"  Fechamento Auto Ativado: {s.closing_time_active}")
        print(f"  Janela: {s.order_opening_time} - {s.order_closing_time}")
        
        is_open = s.is_open()
        print(f"  RESULTADO is_open(): {is_open}")
        
        if s.temp_open_until:
            target = s.temp_open_until
            if target.tzinfo is None:
                target = pytz.timezone('America/Sao_Paulo').localize(target)
            print(f"  Timer de Extensão: {target} (Válido? {now < target})")
        else:
            print(f"  Timer de Extensão: Nenhum")
        print("-" * 30)
