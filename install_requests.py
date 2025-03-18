import os
import tarfile
import urllib.request
import shutil
import sys
import socket

# Adresse IP directe de files.pythonhosted.org (à vérifier si elle est correcte dans votre environnement)
FILES_HOST = "151.101.192.223"
REQUESTS_URL = f"http://{FILES_HOST}/packages/source/r/requests/requests-2.31.0.tar.gz"
REQUESTS_HOST_HEADER = "files.pythonhosted.org"

def download_requests(destination: str):
    """Télécharge l'archive de requests en utilisant l'adresse IP et l'en-tête Host."""
    print(f"Téléchargement de requests depuis {REQUESTS_URL}...")
    request = urllib.request.Request(
        url=REQUESTS_URL,
        headers={"Host": REQUESTS_HOST_HEADER}  # Ajout de l'en-tête Host pour le domaine
    )
    with urllib.request.urlopen(request) as response, open(destination, "wb") as out_file:
        shutil.copyfileobj(response, out_file)
    print(f"Fichier téléchargé : {destination}")

def extract_tar_gz(archive_path: str, extract_to: str):
    """Extrait une archive .tar.gz."""
    print(f"Extraction de l'archive {archive_path}...")
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(path=extract_to)
    print(f"Extraction terminée dans {extract_to}")

def install_to_venv(venv_path: str, source_path: str):
    """Installe la bibliothèque dans le venv."""
    # Vérifier si le venv contient Python
    python_executable = os.path.join(venv_path, "bin", "python") if os.name != "nt" else os.path.join(venv_path, "Scripts", "python.exe")
    if not os.path.exists(python_executable):
        print("Erreur : Python introuvable dans le venv. Vérifiez votre chemin.")
        return

    # Installer requests avec setup.py
    print(f"Installation de requests dans le venv ({venv_path})...")
    setup_path = os.path.join(source_path, "setup.py")
    os.system(f'"{python_executable}" "{setup_path}" install')
    print("Installation terminée.")

def main():
    # Chemins des fichiers
    venv_path = input("Entrez le chemin vers votre venv : ").strip()
    if not os.path.exists(venv_path):
        print("Erreur : le chemin spécifié pour le venv n'existe pas.")
        sys.exit(1)

    temp_dir = "temp_requests"
    archive_path = os.path.join(temp_dir, "requests.tar.gz")
    extracted_path = os.path.join(temp_dir, "requests-2.31.0")  # Nom du dossier après extraction
    
    # Créer un répertoire temporaire
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)

    try:
        # Télécharger et extraire requests
        download_requests(archive_path)
        extract_tar_gz(archive_path, temp_dir)
        
        # Installer requests dans le venv
        install_to_venv(venv_path, extracted_path)
    finally:
        # Nettoyer les fichiers temporaires
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        print("Nettoyage terminé.")

if __name__ == "__main__":
    main()
