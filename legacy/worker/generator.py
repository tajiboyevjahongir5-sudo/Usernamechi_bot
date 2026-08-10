import itertools

def generate_usernames(base_word, limit=100):
    suffixes = ["chi", "lar", "lash", "im", "iy", "uz", "go", "uzb", "pro", "bot"]
    prefixes = ["uz", "the", "my", "pro", "best"]
    
    results = set()
    results.add(base_word)
    
    # Suffixes
    for suf in suffixes:
        results.add(f"{base_word}{suf}")
        
    # Prefixes
    for pref in prefixes:
        results.add(f"{pref}{base_word}")
        
    # Double
    for suf in suffixes:
        for pref in prefixes:
            results.add(f"{pref}{base_word}{suf}")
            
    return list(results)[:limit]
