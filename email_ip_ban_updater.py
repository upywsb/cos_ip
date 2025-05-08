import imaplib
import email
import re
import os
from github import Github

# Konfiguracja
EMAIL = 'your_email@example.com'
PASSWORD = 'your_email_password'
IMAP_SERVER = 'imap.example.com'
GITHUB_TOKEN = 'your_github_token'
REPO_NAME = 'your_username/your_repo'
BRANCH = 'main'
FILE_PATH = 'ban'  # Ścieżka do pliku w repozytorium

def fetch_emails():
    # Połączenie z serwerem IMAP
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    mail.select('inbox')

    # Wyszukiwanie wiadomości z określonym tytułem
    status, messages = mail.search(None, '(SUBJECT "[0250.2025.CTI] Identyfikacja podejrzanej komunikacji sieciowej")')
    ip_addresses = set()

    for num in messages[0].split():
        status, data = mail.fetch(num, '(RFC822)')
        email_msg = email.message_from_bytes(data[0][1])
        
        # Sprawdzenie czy wiadomość ma oczekiwany format TLP
        if '[TLP:AMBER]' not in email_msg.get('Subject', ''):
            continue

        # Parsowanie treści wiadomości
        for part in email_msg.walk():
            if part.get_content_type() == 'text/plain':
                body = part.get_payload(decode=True).decode()
                # Wyszukiwanie adresów IP w treści
                found_ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', body)
                # Usuwanie potencjalnych formatowań (np. 185.119.196[.]20)
                cleaned_ips = [ip.replace('[.]', '.') for ip in found_ips]
                ip_addresses.update(cleaned_ips)

    mail.close()
    mail.logout()
    return ip_addresses

def update_github_file(ip_addresses):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    try:
        # Pobranie aktualnej zawartości pliku
        contents = repo.get_contents(FILE_PATH, ref=BRANCH)
        current_content = contents.decoded_content.decode()
        current_ips = set(current_content.splitlines())
    except:
        current_ips = set()
        current_content = ''

    # Filtracja nowych adresów IP
    new_ips = ip_addresses - current_ips
    
    if new_ips:
        # Dodanie nowych adresów IP do pliku
        updated_content = current_content + '\n' + '\n'.join(new_ips) if current_content else '\n'.join(new_ips)
        
        # Commitujemy zmiany
        repo.update_file(
            path=FILE_PATH,
            message=f'Dodano nowe adresy IP: {", ".join(new_ips)}',
            content=updated_content,
            sha=contents.sha if 'contents' in locals() else None,
            branch=BRANCH
        )
        print(f"Dodano {len(new_ips)} nowych adresów IP do pliku ban.")
    else:
        print("Nie znaleziono nowych adresów IP do dodania.")

if __name__ == '__main__':
    ip_addresses = fetch_emails()
    if ip_addresses:
        update_github_file(ip_addresses)
    else:
        print("Nie znaleziono żadnych adresów IP w wiadomościach.")
