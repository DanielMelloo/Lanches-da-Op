from app import create_app
from database import db
from models import User
from werkzeug.security import generate_password_hash

app = create_app()

def add_master(
    name: str,
    petro_key: str,
    phone: str,
    password: str,
    role: str = "admin_master"
):
    """
    Cria ou atualiza um usuário admin master.

    Parâmetros:
    - name (str): Nome do usuário
    - petro_key (str): Chave Petrobras (4 caracteres)
    - phone (str): Telefone
    - password (str): Senha em texto puro
    - role (str): Papel do usuário (default: admin_master)
    """

    # validação da chave
    if len(petro_key) != 4:
        raise ValueError("A petro_key deve ter exatamente 4 caracteres.")

    with app.app_context():
        existing = User.query.filter_by(petro_key=petro_key).first()
        password_hash = generate_password_hash(password)

        if existing:
            print(f"[INFO] Usuário com KEY '{petro_key}' já existe. Atualizando...")

            existing.name = name
            existing.phone = phone
            existing.role = role
            existing.password_hash = password_hash

            db.session.commit()

            print(
                f"[OK] Usuário atualizado:\n"
                f" - Nome: {existing.name}\n"
                f" - Role: {existing.role}\n"
                f" - Petro Key: {existing.petro_key}"
            )

        else:
            new_user = User(
                name=name,
                petro_key=petro_key,
                phone=phone,
                role=role,
                password_hash=password_hash
            )

            db.session.add(new_user)
            db.session.commit()

            print(
                f"[OK] Novo usuário criado:\n"
                f" - Nome: {new_user.name}\n"
                f" - Role: {new_user.role}\n"
                f" - Petro Key: {new_user.petro_key}"
            )


if __name__ == "__main__":
    # exemplo de uso
    add_master(
        name="Master Admin",
        petro_key="ADMN",
        phone="000000000",
        password="1 ",
        role="admin_master"
    )
