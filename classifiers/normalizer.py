from __future__ import annotations

import re
import unicodedata


def normalize_client_name(name: str) -> str:
    if not name:
        return ""
    
    s = str(name)
    
    # Fix encoding broken chars
    s = s.replace("??", " ")
    s = s.replace("ô", "o")
    s = s.replace("ü", "u")
    
    # Remove accents
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    
    # Lowercase
    s = s.lower()
    
    # Remove common suffixes
    suffixes = [
        r'\s+ltda\s*$',
        r'\s+s[\./]a\s*$',
        r'\s+s/a\s*$',
        r'\s+sa\s*$',
        r'\s+eireli\s*$',
        r'\s+mei\s*$',
        r'\s+ep\s*$',
    ]
    for suffix in suffixes:
        s = re.sub(suffix, '', s, flags=re.IGNORECASE)
    
    # Normalize & to 'e'
    s = s.replace('&', 'e')
    s = s.replace(' / ', ' ')
    
    # Remove extra spaces
    s = re.sub(r'\s+', ' ', s).strip()
    
    return s

def normalize_text(texto) -> str:
    if texto is None:
        return ""
    
    s = str(texto)
    
    # Fix encoding broken chars
    s = s.replace("??", " ")
    s = s.replace("ô", "o")
    s = s.replace("ü", "u")
    
    # Remove accents
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    
    # Lowercase
    s = s.lower()
    
    # Replace newlines
    s = s.replace("\n", " ")
    s = s.replace("\r", " ")
    s = s.replace("\t", " ")
    
    # Remove extra spaces
    s = re.sub(r"\s+", " ", s).strip()
    
    return s

def contains_any(texto_norm: str, termos: list[str]) -> str | None:
    for termo in termos:
        termo_norm = normalize_text(termo)
        if termo_norm and termo_norm in texto_norm:
            return termo
    return None

def resolve_client_group(client_name: str, client_aliases: dict) -> str:
    if not client_name:
        return ""
    
    norm_name = normalize_client_name(client_name)
    
    for group_name, aliases in client_aliases.items():
        for alias in aliases:
            norm_alias = normalize_client_name(alias)
            if norm_alias and norm_alias in norm_name:
                return group_name
    
    return client_name