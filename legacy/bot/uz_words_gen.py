"""
uz_words_gen.py
Tabiiy o'zbekcha so'zlar. 
Sun'iy yopishtirilgan qo'shimchalarsiz faqat ma'noli va hayotiy username bo'la oladigan so'zlar ro'yxati.
"""

UZ_DYNAMIC_WORDS = [
    # IT va Texnologiya
    "dastur", "dasturlar", "dasturchi", "dasturlash", "tizim", "tizimlar", 
    "tarmoq", "tarmoqlar", "ilova", "ilovalar", "sayt", "saytlar", 
    "kompyuter", "koder", "haker", "robot", "suniy", "bilim", "texno", 
    "loyixa", "xizmat", "xizmatlar", "aloqa", "internet",

    # Biznes, Savdo, Moliya
    "dokon", "dokonchi", "savdo", "savdogar", "biznes", "biznesmen", 
    "bozor", "bozorchi", "sotuv", "sotuvchi", "xarid", "xaridor", 
    "pul", "pullar", "daromad", "foyda", "invest", "kredit", "boylik", 
    "moliya", "kassa", "hisob", "narx", "navo", "foydali", "arzon", 
    "qimmat", "tolov", "tolovlar",

    # Vaqt va Holat
    "bugun", "bugungi", "erta", "ertaga", "ertangi", "hozir", "hozirgi", 
    "kecha", "kechagi", "zamon", "zamonaviy", "davr", "vaqt", "kun", 
    "kunlik", "tun", "tungi", "oylik", "yillik", "bahor", "bahorgi", 
    "yozgi", "kuzgi", "qishki", "tong", "tonggi", "oqshom",

    # Kasb va Insonlar
    "muallim", "ustoz", "talaba", "shifokor", "doktor", "haydovchi", 
    "usta", "rahbar", "boshliq", "lider", "admin", "menejer", "direktor",
    "yozuvchi", "shoir", "qoshiqchi", "sanatkor", "sportchi", "oquvchi",
    "xodim", "ishchi", "hunarmand", "tadbirkor", "dizayner",

    # Sifat va Hissiyotlar
    "sevimli", "sevgim", "yaxshi", "yangi", "eski", "gozal", "shirin", 
    "kuchli", "aqlli", "dono", "tezkor", "ajoyib", "qiziq", "qiziqarli", 
    "baxt", "baxtli", "omad", "omadli", "quvonch", "kulgu", "mehr", 
    "mehrli", "orzu", "umid", "niyat", "tilak", "halol", "toza", "pok", 
    "sodiq", "botir", "jasur", "chiroyli", "asl", "zoor", "qadrli", 
    "ishonch", "ishonchli", "xursand", "haqiqiy",

    # Hayot va Jamiyat
    "hayot", "hayotiy", "vatan", "xalq", "inson", "odam", "dunyo", 
    "olam", "shahar", "qishloq", "mahalla", "kocha", "uy", "uylar", 
    "oila", "oilaviy", "farzand", "bola", "bolalar", "qizlar", "yigit", 
    "yigitlar", "dost", "dostlar", "dostlik", "kelajak", "tarix", 
    "madaniyat", "tinchlik", "soglik", "salomat",

    # Tabiat va Predmetlar
    "osmon", "quyosh", "oy", "yulduz", "yulduzlar", "bulut", "yomgir", 
    "qor", "shamol", "tog", "toglar", "tosh", "daryo", "dengiz", "suv", 
    "gul", "gullar", "daraxt", "meva", "mevalar", "olma", "anor", "uzum", 
    "non", "osh", "choy", "kitob", "kitoblar", "kitobxon", "daftar", 
    "qalam", "maktab", "dars", "ilm", "fan", "sport", "oyin", "oyinlar", 
    "kino", "musiqa", "sanat", "sovgak", "hadya", "kiyim", "poyabzal",
    
    # Ranglar
    "oq", "qora", "qizil", "sariq", "yashil", "kok", "moviy", "pushti",

    # Joynomalar va Umumiy
    "markaz", "hudud", "maydon", "oliygoh", "akademiya", "institut", 
    "fakultet", "guruh", "kanal", "guruhlar", "kanallar", "chat", 
    "elon", "elonlar", "yangilik", "yangiliklar", "xabar", "xabarlar", 
    "malumot", "baza", "savol", "javob", "muammo", "yechim",
]

# Dinamik nom qoldirildi (words.py buzilmasligi uchun) lekin ichida statik sifatli so'zlar bor
