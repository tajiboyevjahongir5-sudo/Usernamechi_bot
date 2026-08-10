"""
words.py — Keng qamrovli username so'z bazasi
Maqsad: 3000+ curated so'z + 41k lug'at = maksimal bo'sh username topish
"""
import random
import os

def _is_pronounceable(word: str) -> bool:
    vowels = set('aeiou')
    cons_run = vowel_run = 0
    for ch in word.lower():
        if ch in vowels:
            cons_run = 0; vowel_run += 1
            if vowel_run > 3: return False
        elif ch.isalpha():
            vowel_run = 0; cons_run += 1
            if cons_run > 3: return False
        else:
            cons_run = vowel_run = 0
    return True

# ════════════════════════════════════════════════════════
#  O'ZBEK ERKAK ISMLAR  (~200)
# ════════════════════════════════════════════════════════
UZ_MALE_NAMES = [
    "abdulloh","abrorbek","abror","acilbek","adham","adiz","afzal",
    "akbar","akmal","akrom","alaskar","alibek","alisher","alixon",
    "aliyev","almazbek","alp","alpomish","altoy","amirxon","anvar",
    "anvarjon","arslonbek","arslon","asadbek","asad","askar","asliddin",
    "asliddin","aslonbek","aslbek","asom","azizbek","aziz","azizjon",
    "bahodir","baxtiyor","baxrom","behruz","behzod","bekhruz","bekhzod",
    "bekmurod","bektosh","bekzod","bobur","boburjon","boltaboy","botir",
    "bunyod","bunyodbek","damon","daniyor","davron","davlat","diyorbek",
    "diyorjon","diyor","doston","dostonbek","eldor","elmurod","elshod",
    "elyor","elbek","elmurat","erkin","fakhriddin","faridun","farrukh",
    "farrux","farrukhjon","farhodjon","farhod","firdavs","firdavsbek",
    "fozil","furqat","giyos","hamid","hamidjon","hamza","hayot","husan",
    "husayn","husniddin","ibrohim","ikrom","ilhom","iskandar","islom",
    "ismoil","ismoilov","izzat","izzatulloh","jabborov","jahon",
    "jahongir","jaloliddин","jamshid","jasur","jasurbek","javlon",
    "jaxongir","jonibek","joniyor","jorabek","kamoliddin","kamol",
    "kamolbek","komil","komiljon","lochin","laziz","lazizjon","lutfillo",
    "maftun","mansur","mansurjon","mirzo","mirjalol","mirzohid",
    "mirzokarim","mirzoxid","muazzam","mukhlis","muhammadali",
    "muhammadjon","muhammadsaid","muhiddin","mukhammad","murod",
    "murodali","murodjon","mustafo","muzaffar","muzaffarjon","nafosatov",
    "narzulloh","nodir","nodirjon","nozim","nozimjon","nurbek","nuriddin",
    "nurillo","nurillojon","nurmamat","nusrat","obid","odil","odiljon",
    "oybek","oybekjon","ozod","ozodjon","parviz","parvizjon","pulat",
    "qodir","qodirjon","quvondiq","ravshan","ravshanbek","raxmatullo",
    "razzaq","rustam","rustamjon","saidakbar","saidali","samandar",
    "samir","sanjar","sanjarbek","sarvar","sarvarbek","sarvarjon",
    "shamsiddin","sherzod","sherzodjon","shohruh","shokir","shodmon",
    "shodmanov","sirojiddin","sobir","sohibjon","sulton","sunnat",
    "tahsin","temur","temurbek","temurlan","tohir","tohirjon","toxir",
    "toxirjon","umar","umid","umidjon","umer","urfon","utkirbek","vohid",
    "vohidjon","xasan","xasanjon","xolmat","xolmatov","xurshid",
    "xurshidjon","xushnud","xusan","yakubov","yorqin","yorqinjon",
    "yusuf","yusufjon","zafar","zafarjon","zubaydullo","zuhriddin",
    "zukhriddin","ulugbek","ulmas","ulfat","utkir","valijon","valixon",
    "xamza","xasan","xoliqov","xorun","yunusov","zokirov","elbek",
    "elbekjon","aliqul","aliqulов","asilbek","asiljon","atobek",
    "atobioy","axror","axrorjon","azamat","azamatjon","baxtiyorjon",
    "baxtiyor","dostonali","eldorbek","elmurod","faridjon","farhiddin",
    "hamidulloh","hayotbek","ikromjon","ilhomjon","iskandarjon",
    "jabborjon","komilbek","lochinbek","mansurbek","mirjaloljon",
    "mukhammadali","muhammadsaид","murodulloh","narzullo","nodirjon",
    "nozimjon","nurillojon","odilbek","oybekjon","parvizjon","qodirjon",
    "ravshanbek","rustambek","saidalibek","sanjarbek","sarvarjon",
    "shohruhjon","shodmonov","sobironov","sultonbek","tahsinjon",
    "temurbekjon","toxirjon","umidjon","utkirjon","xasanjon","xurshidjon",
]

# ════════════════════════════════════════════════════════
#  O'ZBEK AYOL ISMLAR  (~150)
# ════════════════════════════════════════════════════════
UZ_FEMALE_NAMES = [
    "adolat","aziza","azizaxon","aziza","barno","barnogul",
    "barnoxon","baхor","charos","charos","charos","dildora",
    "dilorom","dilnoza","dilnur","dilrabo","dilrabo","dilfuza",
    "ezgulik","farzona","farzona","feruza","feruzaxon","fotima",
    "fotimaxon","gavhar","gavhargul","gulbahor","gulnora","gulnoz",
    "gulchеxra","gulruh","gulsum","gulyuz","hamida","hayot",
    "hulkar","hulkarbonu","hurriyat","husniya","husnora","iroda",
    "irodaxon","kamola","kamolaxon","komila","kumush","lola",
    "lobar","lobarxon","lutfiya","maftuna","mahliyo","mahzuna",
    "malika","malikaxon","manzura","mavluda","mavludaxon","mehribon",
    "mekhribonu","mohichehra","mohira","mohlaroyim","mohlaroyim",
    "mohinur","mohlar","muazzam","muazzama","munira","muniraxon",
    "musharraf","mushtariy","nargiza","nargizaxon","nasiba","nasibaxon",
    "nazokat","nazokatxon","nigora","nigoraxon","nilufar","nilufarxon",
    "nодira","nodirabonu","nodiraxon","nozima","nozimaxon","noziya",
    "noziyaxon","nuriya","nuriniso","nurinur","nurzoda","oydin",
    "oydinxon","oygul","oymomo","oysha","oyshaxon","ozoda","ozodaxon",
    "parizod","parizodxon","ra'no","rahima","rano","rohila",
    "rohilaxon","roxila","sabohat","sadoqat","sanam","sanamxon",
    "sanobar","saodat","saodatxon","sarvinoz","sarvinozxon","saydaxon",
    "sevara","sevaraxon","shahnoza","shahnozaxon","shahlo","shahloxon",
    "shaxlo","shaxloxon","shirin","shirinxon","soliha","solihaxon",
    "surayyo","surayyoxon","tabassum","tabassuм","tursunoy","ulmas",
    "xilola","xilolaxon","xurmo","xurshida","yulduz","yulduzxon",
    "zilola","zilolaxon","zinnat","zuhra","zuhrabonu","zulfiya",
    "zulfiyaxon","zumrad","nafosa","nafosatxon","nafosatov","maftunaxon",
    "mehribonu","mohicheхra","mohinurxon","muazzamaxon","musharrafxon",
    "nazokatxon","nigoraxon","nurinisoxon","oydинxon","parizodxon",
    "rahimaxon","ranoхon","rohilaxon","sabohatxon","sadoqatxon",
    "sanobara","shahnozaxon","shirinxon","soliхaxon","surayyoxon",
    "tabassuмxon","xilolaxon","yulduzxon","zilolaxon","zuhraxon",
    "adolatxon","barnoxon","dildoraxon","diloromxon","dilnozaxon",
    "farzonaxon","fotimaxon","gavharxon","gulnoraxon","hamidaxon",
    "irodaxon","kamolaxon","kumusxon","lobarxon","mahzunaxon",
    "malikaxon","mehribonxon","muniraxon","narginaxon","nodiraxon",
]

# ════════════════════════════════════════════════════════
#  O'ZBEK FAMILIYALAR  (~150)
# ════════════════════════════════════════════════════════
UZ_SURNAMES = [
    "abdullayev","abdullayeva","abduraxmonov","adizov","akhmedov",
    "alimov","aliyev","aripov","askarov","atajonov","atamuratov",
    "ataxonov","avazov","axmedov","axmedova","azimov","baxtiyorov",
    "botirov","boymurodov","choriyev","davlatov","dusmatov","eshmatov",
    "ergashev","ergasheva","fozilов","fozilova","ganiyev","hamidov",
    "hamidova","hasanov","hasanova","haydarov","holiqov","ibragimov",
    "ismoilov","ismoilova","jalolov","jalolova","jumayev","karimov",
    "karimova","komilov","komilovа","mamatov","mamatova","mansupov",
    "mirzayev","mirzayeva","murodov","murodova","musayev","nazarov",
    "nazarova","nishonov","normatov","normatova","ochilov","ochilova",
    "olimov","olimova","ortiqov","ortiqova","pulatov","pulatova",
    "qodirov","qodirova","qosimov","qosimova","rahimov","rahimova",
    "rашидов","rashidova","razzaqov","razzaqova","rustamov","rustamova",
    "saidov","saidova","salimov","salimova","saydullayev","sharipov",
    "sharipova","sobirov","sobirova","sultonov","sultonova","tashmatov",
    "tashmatova","tojiboyev","tojiboyeva","toshmatov","toshmatova",
    "toxirov","toxirova","tursunov","tursunova","umarov","umarova",
    "usmonov","usmonova","valiyev","valiyeva","xolmatov","xolmatova",
    "xoliqov","xoliqova","xasanov","xasanova","yusupov","yusupova",
    "yunusov","yunusova","zaripov","zaripova","zokirov","zokirova",
    "zufarov","zufarova","abdujabborov","abdurahmonov","abduraxmonova",
    "akhmedova","alimova","aripova","askarova","atajonova","avazova",
    "azimova","baxtiyorova","botirovа","boymurodova","davlatova",
    "dusmatova","eshmatova","ergashova","ganiyeva","haydarova",
    "holiqova","ibragimova","jalolova","jumayeva","mamatova","mansupova",
    "mirzayeva","musayeva","nazarova","nishonova","normatova","ochilova",
    "olimova","ortiqova","pulatova","qodirova","qosimova","rahimova",
    "razzaqova","rustamova","saidova","salimova","sharipova","sobirova",
    "sultonova","tashmatova","tojiboyeva","toshmatova","toxirova",
    "tursunova","umarova","usmonova","valiyeva","xolmatova","yusupova",
    "yunusova","zaripova","zokirova","zufarova",
]

# ════════════════════════════════════════════════════════
#  O'ZBEK UMUMIY SO'ZLAR  (~200)
# ════════════════════════════════════════════════════════
UZ_WORDS_ALL = [
    # Tabiat
    "bahor","yoz","kuz","qish","shamol","yomgir","quyosh","osmon",
    "bulut","daryo","dengiz","toglar","sahro","vodiy","daraxt","gul",
    "barg","meva","tosh","tuproq","qum","muzlik","sharshara","kolon",
    "tepa","jarlik","botqoq","ovul","qishloq","shahar","mahalla",
    # Fazilatlar
    "yaxshi","yomon","kuchli","zaif","aqlli","nodon","dono","ahmoq",
    "botir","qoqon","jasur","qoqon","gozal","xunuk","shirin","achchiq",
    "saxiy","xasis","kamtar","manman","sadiq","xoin","vafodor","bevafo",
    "mehribon","qattiqqol","yumshoq","qattiq","yengil","og'ir",
    # Hayot
    "hayot","olim","baxt","orzu","sevgi","nafrat","quvonch","qayg'u",
    "kulgu","yig'i","do'st","dushman","ota","ona","aka","uka","opa",
    "singil","bola","qiz","o'g'il","oila","uy","bino","ko'cha","bog'",
    # Kasb
    "doktor","muallim","ustoz","talaba","hunarmand","dehqon","savdogar",
    "harbiy","politsiya","muxbir","rassom","musiqachi","sportchi",
    "haydovchi","pilot","dengizchi","oshpaz","tikuvchi","novvoy",
    # Texnologiya
    "raqamli","tezkor","zamonaviy","ilg'or","yangi","eski","kuchli",
    "dastur","ilova","internet","kompyuter","telefon","kamera","radio",
    "televizor","robot","sun'iy","raqam","signal","tizim","tarmoq",
    # Iqtisodiyot
    "savdo","biznes","moliya","bank","kapital","daromad","invest",
    "bozor","narx","pul","tangа","boylik","qashshoqlik","kredit",
    "ssuda","qarz","foyda","zarar","raqobat","monopoliya",
    # Joy nomlari
    "toshkent","samarqand","buxoro","namangan","andijon","fargona",
    "termiz","nukus","qarshi","gulistan","jizzax","navoiy","urganch",
    "marg'ilon","kokand","shahrisabz","denov","hazorasp",
    # Sport
    "futbol","basketball","kurash","boks","karate","judo","suzish",
    "yugurish","sakrash","otish","tennis","voleybol","xokkey",
    # Hayvonlar (o'zbek)
    "lochin","burgut","qoqnur","bulbul","bedana","kaklik","laylak",
    "qarg'a","musicha","kaptar","it","mushuk","ot","sigir","qo'y",
    "echki","tuya","fil","sher","yo'lbars","bo'ri","tulki","quyon",
    "sincap","eshak","xo'kiz","buqa","temir","oltin","kumush","mis",
    # Turli
    "dunyo","zamon","maktab","kitob","bilim","fan","tarix","san'at",
    "madaniyat","til","yozuv","music","kino","teatr","muzey","galeriya",
    "masjid","cherkov","bozor","restoran","mehmonxona","aeroportu",
    "temir","xoda","oltin","kumush","bronza","temir","po'lat","mis",
    "shisha","yog'och","tosh","beton","g'isht","qovoq","qozon",
    "galaba","zafar","g'alaba","yutuq","mag'lubiyat","bahona",
    "ezgu","olijanob","sharaf","or-nomus","vijdon","himmat",
    # Yangi kiritilgan: fel-atvor, kasb, brend, mashhur ism/mansab, va hajviy
    "halol", "mehnatkash", "sabrli", "jasur", "irodali", "odil", "samimiy", "fidoyi", "chaqqon", "zukko",
    "quruvchi", "muhandis", "tadbirkor", "rahbar", "usta", "sotuvchi", "shifokor", "dasturchi", "hunarmand",
    "reklama", "sifat", "kiyim", "avto", "mebel", "xizmat", "brend", "savdo", "bozor",
    "quvnoq", "kulgili", "antiqa", "zo'r", "super", "hajviy", "ajoyib", "qiziqarli",
    "vazir", "hokim", "rais", "direktor", "boshliq", "general", "kapitan", "lider",
    "yoldosh", "beruniy", "navoiy", "temur", "bobur", "mirzo", "sulton", "amir"
]

# ════════════════════════════════════════════════════════
#  INGLIZ ERKAK ISMLAR  (~200)
# ════════════════════════════════════════════════════════
EN_MALE_NAMES = [
    "aaron","adam","aiden","alan","alex","alexis","alfred","alvin",
    "andrew","andy","angel","archer","arthur","austin","axel",
    "ayden","ben","blake","brad","brady","brandon","brian","bruce",
    "bryan","bryce","caleb","calvin","cameron","carlos","carter",
    "chance","charles","chase","chris","christian","clark","clay",
    "cody","cole","colin","conor","cooper","corey","cory","craig",
    "curtis","dallas","dan","daniel","dante","darius","darren",
    "darryl","david","dean","derek","devin","devyn","dillon","dominic",
    "donald","douglas","drew","dustin","dylan","edgar","edward",
    "elias","elijah","emilio","eric","ethan","evan","ezra","felix",
    "finn","frank","frankie","gabriel","garrett","gavin","george",
    "graham","grant","greg","griffin","gus","hayden","henry","hugo",
    "hunter","ian","isaac","isaiah","ivan","jack","jackson","jacob",
    "jake","james","jason","javier","jayden","jc","jed","jeff",
    "jeremy","jesse","joaquin","joel","john","johnny","jon","jonathan",
    "jordan","joseph","josh","joshua","juan","julian","justin",
    "kai","karter","keith","kendall","kevin","kieran","kyle","lance",
    "landon","leo","leon","liam","logan","lucas","luke","marcus",
    "mario","mark","martin","mason","matthew","max","michael","miguel",
    "miles","mitchell","morgan","nate","nathan","neil","nicholas",
    "nick","nico","noel","nolan","noah","oliver","oscar","owen",
    "parker","patrick","paul","pedro","peter","phillip","pierce",
    "quinn","raphael","raymond","reuben","richard","riley","rob",
    "robert","roberto","rodrigo","roman","ross","ryder","ryan",
    "sam","samuel","scott","sean","seth","shaun","simon","stefan",
    "stephen","steven","thomas","timothy","tobias","tom","tommy",
    "travis","trevor","tristan","tucker","tyler","vincent","wade",
    "warren","will","william","wyatt","xander","xavier","zach",
    "zachary","zane","zero","zion",
]

# ════════════════════════════════════════════════════════
#  INGLIZ AYOL ISMLAR  (~150)
# ════════════════════════════════════════════════════════
EN_FEMALE_NAMES = [
    "abby","abigail","ada","addison","adriana","aiden","alexa",
    "alexis","alice","alicia","alina","alison","aliya","allison",
    "amanda","amara","amber","amelia","amy","ana","andrea","angel",
    "anna","aria","ariana","ariel","ashley","aubrey","audrey","aurora",
    "ava","avery","bailey","bella","bianca","brenda","brianna",
    "brittany","caitlyn","callie","camila","cara","cassandra","cassie",
    "charlotte","chloe","christa","claire","clara","claudia","cora",
    "dana","daniela","destiny","diana","eleanor","elena","eliana",
    "elisa","eliza","elizabeth","ella","ellie","emily","emma",
    "evelyn","faith","felicia","fiona","freya","gabriela","genesis",
    "gemma","grace","hailey","hanna","harper","hazel","heather",
    "helen","holly","hope","iris","isabella","isla","ivy","jade",
    "jasmine","jenna","jennifer","jessica","jordan","josephine",
    "josie","julia","juliana","kaitlyn","karen","kate","katie",
    "kayla","kelly","khloe","kiersten","kira","kylie","layla",
    "leah","leila","lily","lisa","lola","lorelei","luna","lydia",
    "mackenzie","madison","maggie","maia","mallory","margaret",
    "maria","marisol","maya","megan","melissa","mia","michelle",
    "mila","miranda","molly","morgan","naomi","natalia","natalie",
    "natasha","nena","nicky","nora","nova","olivia","paige","paola",
    "penelope","phoebe","piper","quinn","rachel","reagan","rebecca",
    "riley","rose","ruby","samantha","sandy","sara","sarah","savannah",
    "selena","sierra","skylar","sofia","sophia","stella","stephanie",
    "sydney","taylor","tessa","tina","tori","valentina","vanessa",
    "victoria","violet","vivian","wendy","willow","xena","yasmin",
    "zoe","zoey","zora",
]

# ════════════════════════════════════════════════════════
#  HAYVON NOMLARI  (~300)
# ════════════════════════════════════════════════════════
ANIMALS_ALL = [
    # Yirik yirtqichlar
    "lion","tiger","leopard","jaguar","cheetah","puma","cougar",
    "panther","lynx","ocelot","caracal","serval","bobcat","margay",
    "clouded","wolf","coyote","jackal","hyena","dingo","dhole",
    "bear","grizzly","kodiak","panda","polar","sloth","sun",
    # Kichik yirtqichlar
    "fox","fennec","corsac","arctic","swift","marten","badger",
    "ferret","weasel","stoat","mink","otter","skunk","wolverine",
    "mongoose","meerkat","suricate","civet","genet","binturong",
    "raccoon","coati","kinkajou","ringtail","opossum","possum",
    # Dengiz sutemizuvchilari
    "dolphin","porpoise","orca","beluga","narwhal","sperm","blue",
    "humpback","minke","finback","bowhead","right","gray","sei",
    "walrus","seal","sealion","weddell","crabeater","leopard",
    "monk","elephant","bearded","ringed","harp","hooded","ribbon",
    # Qushlar
    "eagle","falcon","hawk","osprey","kestrel","merlin","hobby",
    "harrier","condor","vulture","buzzard","kite","accipiter",
    "goshawk","sparrow","raven","crow","magpie","jackdaw","rook",
    "jay","nuthatch","creeper","wren","robin","thrush","blackbird",
    "starling","sparrow","finch","canary","goldfinch","siskin",
    "linnet","redpoll","crossbill","bullfinch","hawfinch","grosbeak",
    "bunting","lark","pipit","wagtail","dipper","kingfisher",
    "martin","swallow","swift","owl","barn","eagle","snowy","tawny",
    "great","little","short","long","pygmy","hawk","eagle","fishing",
    "crane","heron","egret","ibis","stork","spoonbill","flamingo",
    "pelican","cormorant","gannet","booby","frigatebird","albatross",
    "petrel","shearwater","penguin","puffin","auk","guillemot",
    "razorbill","murre","tern","gull","skua","jaeger","skimmer",
    "parrot","macaw","cockatoo","cockatiel","parakeet","lory",
    "lorikeet","toucan","hornbill","woodpecker","flicker","sapsucker",
    "peacock","turkey","pheasant","grouse","partridge","quail",
    "guinea","ostrich","emu","rhea","cassowary","kiwi","takahe",
    # Suv hayvonlari
    "shark","whale","ray","skate","chimaera","coelacanth","sturgeon",
    "salmon","trout","bass","perch","pike","carp","catfish","eel",
    "moray","barracuda","swordfish","marlin","tuna","mackerel",
    "herring","sardine","anchovy","cod","haddock","pollock","halibut",
    "flounder","sole","turbot","plaice","dab","brill","megrim",
    "octopus","squid","cuttlefish","nautilus","clam","oyster","mussel",
    "scallop","abalone","conch","whelk","periwinkle","limpet",
    "lobster","crayfish","crab","shrimp","prawn","krill","barnacle",
    # Sutemizuvchilar
    "elephant","rhino","hippo","giraffe","zebra","wildebeest",
    "hartebeest","gnu","impala","gazelle","springbok","eland","kudu",
    "nyala","bushbuck","bongo","duiker","dik","steenbok","grysbok",
    "klipspringer","reedbuck","waterbuck","kob","lechwe","puku",
    "sable","roan","gemsbok","oryx","addax","bontebok","blesbok",
    "topi","tsessebe","damalisk","bison","buffalo","gaur","banteng",
    "yak","musk","moose","elk","caribou","reindeer","deer","fallow",
    "roe","muntjac","sika","axis","sambar","barasingha","swamp",
    "llama","alpaca","vicuna","guanaco","camel","dromedary","donkey",
    "horse","pony","mule","zebra","tapir","rhino","horse","pig",
    "boar","peccary","warthog","hippo","capybara","nutria","beaver",
    "porcupine","hedgehog","platypus","echidna","kangaroo","wallaby",
    "quokka","wombat","koala","tasmanian","numbat","quoll","possum",
    "glider","bandicoot","dunnart","antechinus","phascogale",
    "gorilla","chimp","bonobo","orangutan","gibbon","siamang",
    "baboon","mandrill","gelada","macaque","langur","proboscis",
    "howler","spider","squirrel","capuchin","marmoset","tamarin",
    # Sudralib yuruvchilar
    "cobra","mamba","viper","python","anaconda","boa","king","coral",
    "rattler","sidewinder","copperhead","cottonmouth","taipan",
    "adder","racer","whip","garter","ribbon","hognose","water",
    "gecko","iguana","monitor","komodo","beaded","skink","anole",
    "chameleon","agama","frilled","horned","thorny","moloch",
    "crocodile","alligator","caiman","gharial","tortoise","turtle",
    # Hasharotlar
    "mantis","hornet","wasp","bee","bumblebee","honeybee","mason",
    "carpenter","leafcutter","fire","bullet","driver","army",
    "butterfly","moth","hawk","swallowtail","monarch","painted",
    "admiral","peacock","brimstone","orange","comma","fritillary",
    "beetle","stag","rhinoceros","goliath","tiger","ground","diving",
    "dragonfly","damselfly","mayfly","stonefly","caddisfly","lacewing",
    "cricket","grasshopper","locust","katydid","stick","leafinsect",
    "praying","mantis","walkingstick","earwig","silverfish","firebrat",
    # Qo'shimcha o'zbek
    "lochin","burgut","qoqnur","bulbul","bedana","kaklik","laylak",
    "qarg'a","musicha","kaptar","ilon","kaltakesak","toshbaqa",
]

ANIMALS_CLEAN = sorted(set(
    a.lower() for a in ANIMALS_ALL
    if a.isalpha() and 5 <= len(a) <= 8 and _is_pronounceable(a)
))

# ════════════════════════════════════════════════════════
#  TABIAT, MINERALLAR, GEO  (~200)
# ════════════════════════════════════════════════════════
NATURE_ALL = [
    # Minerallar va qimmatbaho toshlar
    "onyx","amber","garnet","jasper","opal","topaz","zircon","quartz",
    "agate","obsidian","granite","marble","basalt","pumice","flint",
    "cobalt","silver","golden","ivory","ebony","coral","pearl",
    "ruby","emerald","diamond","sapphire","amethyst","turquoise",
    "lapis","malachite","rhodonite","fluorite","calcite","gypsum",
    "mica","feldspar","hornblende","augite","olivine","pyroxene",
    "spinel","garnet","grossular","almandine","pyrope","andradite",
    "uvarovite","spessartine","tsavorite","demantoid","hessonite",
    "zoisite","tanzanite","iolite","kyanite","sillimanite","andalusite",
    # Tabiat hodisalari
    "storm","thunder","lightning","tornado","hurricane","typhoon",
    "cyclone","blizzard","avalanche","landslide","earthquake",
    "tsunami","eruption","geyser","hotspring","volcano","caldera",
    "frost","ice","snow","hail","rain","drizzle","fog","mist",
    "cloud","cumulus","stratus","nimbus","cirrus","cumulonimbus",
    "aurora","rainbow","mirage","halos","corona","zodiacal",
    "comet","meteor","asteroid","nebula","galaxy","pulsar","quasar",
    "solstice","equinox","eclipse","transit","occultation",
    "zenith","nadir","meridian","azimuth","altitude","declination",
    # Joy shakllari
    "mountain","volcano","hill","cliff","ridge","escarpment",
    "valley","canyon","gorge","ravine","gulch","gully","defile",
    "plateau","mesa","butte","pinnacle","spire","tower","needle",
    "plain","prairie","steppe","savanna","tundra","taiga","boreal",
    "forest","jungle","rainforest","mangrove","swamp","marsh","bog",
    "delta","estuary","lagoon","bay","gulf","strait","channel",
    "fjord","inlet","cove","harbor","haven","port","reef","shoal",
    "island","peninsula","isthmus","cape","headland","promontory",
    "glacier","icefield","icecap","iceberg","floe","pack","fast",
    "river","stream","brook","creek","rivulet","torrent","rapids",
    "waterfall","cascade","cataract","spring","well","aquifer",
    "lake","pond","pool","reservoir","oasis","cenote","sinkhole",
    "cave","cavern","grotto","karst","stalactite","stalagmite",
    # O'simliklar
    "cedar","birch","maple","aspen","willow","poplar","alder",
    "oak","elm","ash","beech","hornbeam","linden","hazel","hawthorn",
    "rowan","elder","holly","ivy","fern","moss","lichen","algae",
    "lotus","daisy","lilac","lavender","rose","iris","tulip","orchid",
    "lily","poppy","sunflower","chrysanthemum","dahlia","peony",
    "cactus","agave","aloe","bamboo","bonsai","cypress","juniper",
    "yew","pine","spruce","fir","larch","hemlock","redwood","sequoia",
    "baobab","acacia","eucalyptus","banyan","mangrove","palm",
    # Astro / kosmik
    "solar","lunar","stellar","cosmic","astral","orbital","galactic",
    "nebular","pulsar","quasar","photon","neutrino","graviton",
    "antimatter","darkmatter","spacetime","wormhole","singularity",
    "blackhole","neutron","proton","electron","quantum","plasma",
]

NATURE_CLEAN = sorted(set(
    w.lower() for w in NATURE_ALL
    if w.isalpha() and 5 <= len(w) <= 8 and _is_pronounceable(w)
))

# ════════════════════════════════════════════════════════
#  INGLIZCHA COOL SO'ZLAR  (~300)
# ════════════════════════════════════════════════════════
EN_COOL_ALL = [
    # Xarakter / laqam
    "ghost","shadow","phantom","cipher","ranger","hunter","outlaw",
    "nomad","archer","knight","herald","rogue","maverick","pioneer",
    "voyager","pilgrim","wanderer","sentinel","guardian","champion",
    "warrior","wizard","alchemist","oracle","prophet","sage","monk",
    "paladin","warlock","shaman","druid","bard","assassin","ninja",
    "samurai","ronin","viking","raider","berserker","gladiator",
    "spartan","legionnaire","centurion","prefect","praetor","consul",
    "tribune","legate","quaestor","aedile","praetor","dictator",
    # Tabiat (ingliz)
    "blaze","surge","storm","frost","ember","comet","lunar","solar",
    "aurora","zenith","nadir","vortex","tempest","torrent","rapids",
    "glacier","avalanche","tsunami","cyclone","typhoon","hurricane",
    # Texnologiya
    "pixel","vector","cipher","kernel","socket","relay","lambda",
    "tensor","proxy","cache","script","daemon","beacon","signal",
    "pulse","nexus","vertex","matrix","binary","quantum","crypto",
    "neural","digital","analog","optical","photon","laser","radar",
    "sonar","lidar","gnss","gps","rfid","nfc","bluetooth","wifi",
    "ethernet","protocol","packet","router","switch","gateway",
    "firewall","vpn","proxy","torrent","peer","node","cluster",
    "server","client","database","schema","query","index","cache",
    "buffer","stack","heap","queue","tree","graph","hash","map",
    "vector","array","matrix","tensor","scalar","complex","fourier",
    # Sifatlar (username bo'la oladi)
    "vivid","stark","brisk","crisp","sleek","prime","swift","blaze",
    "surge","bold","brave","deft","keen","pure","apex","peak","elite",
    "ultra","hyper","turbo","mega","super","alpha","omega","sigma",
    "delta","theta","gamma","lambda","kappa","epsilon","zeta","eta",
    "iota","upsilon","phi","chi","psi","rho","nu","mu","xi","pi",
    # Biznes / brend
    "venture","anchor","bridge","harbor","forge","atlas","vault",
    "haven","citadel","bastion","pinnacle","summit","zenith","apex",
    "prime","elite","luxury","premium","ultimate","infinite","eternal",
    "imperial","royal","noble","regal","grand","majestic","sovereign",
    "supreme","paramount","cardinal","primal","primordial","ancient",
    "mythic","legendary","epic","iconic","classic","vintage","timeless",
    # Harakatlar
    "dominate","conquer","achieve","triumph","prevail","succeed",
    "excel","advance","ascend","elevate","enhance","amplify","boost",
    "propel","launch","deploy","execute","deliver","perform","achieve",
    # Ranglar
    "crimson","scarlet","azure","cobalt","violet","magenta","amber",
    "golden","silver","ivory","ebony","onyx","obsidian","charcoal",
    "slate","pewter","bronze","copper","brass","chrome","platinum",
    "indigo","teal","cyan","turquoise","emerald","jade","forest",
    "olive","lime","sage","mint","aqua","navy","royal","midnight",
    "burgundy","maroon","wine","rust","brick","terracotta","ochre",
    "sienna","umber","sepia","taupe","beige","cream","pearl","bone",
    "linen","khaki","sand","dune","desert","tan","caramel","cinnamon",
    "mocha","espresso","mahogany","walnut","cedar","chestnut","auburn",
    "russet","coral","salmon","peach","apricot","citrus","lemon",
    "canary","chartreuse","pear","pistachio","fern","moss","pine",
    "spruce","glacier","steel","stone","pewter","flint","graphite",
    # O'yin / esports
    "ranked","clutch","frenzy","lethal","turbo","stealth","tactical",
    "strategic","precision","accuracy","headshot","quickscope",
    "oneshot","sniper","rifler","lurker","flanker","rusher","anchor",
    "fragger","entry","support","awper","igl","captain","coach",
    "analyst","scout","recon","assault","heavy","medic","engineer",
    "demolition","infiltrator","operative","agent","handler","handler",
]

EN_COOL_CLEAN = sorted(set(
    w.lower() for w in EN_COOL_ALL
    if w.isalpha() and 5 <= len(w) <= 8 and _is_pronounceable(w)
))

# ════════════════════════════════════════════════════════
#  FILTERED CLEAN VERSIONS
# ════════════════════════════════════════════════════════
UZ_WORDS_CLEAN = sorted(set(
    (w.lower() for w in UZ_WORDS_ALL if w.isalpha() and 5 <= len(w) <= 12)
))

# Kengaytirilgan o'zak-qo'shimchali so'zlar: bugungi, dasturlash, dokonchi...
try:
    from bot.uz_words_gen import UZ_DYNAMIC_WORDS
    UZ_WORDS_CLEAN = sorted(set(UZ_WORDS_CLEAN).union(set(UZ_DYNAMIC_WORDS)))
except Exception as e:
    pass

UZ_WORDS = UZ_WORDS_CLEAN + [
    n for n in UZ_MALE_NAMES + UZ_FEMALE_NAMES
    if n.isalpha() and 5 <= len(n) <= 12
]
UZ_SHORT = UZ_WORDS

EN_ALL_POOL = list(set(
    [n for n in EN_MALE_NAMES + EN_FEMALE_NAMES if n.isalpha() and 5 <= len(n) <= 8]
    + ANIMALS_CLEAN + NATURE_CLEAN + EN_COOL_CLEAN
))
EN_WORDS_COMMON = EN_ALL_POOL
EN_COOL = EN_ALL_POOL

# ════════════════════════════════════════════════════════
#  LEKSIKON (fayldan)
# ════════════════════════════════════════════════════════
adjectives = []
nouns = []

try:
    adj_path = os.path.join(os.path.dirname(__file__), 'adjectives.txt')
    with open(adj_path, 'r', encoding='utf-8') as f:
        adjectives = [
            w for w in (line.strip().lower() for line in f)
            if w.isalpha() and 5 <= len(w) <= 8 and _is_pronounceable(w)
        ]
except Exception:
    adjectives = ["vivid","sleek","stark","crisp","swift","bold","prime"]

try:
    noun_path = os.path.join(os.path.dirname(__file__), 'nouns.txt')
    with open(noun_path, 'r', encoding='utf-8') as f:
        nouns = [
            w for w in (line.strip().lower() for line in f)
            if w.isalpha() and 5 <= len(w) <= 8 and _is_pronounceable(w)
        ]
except Exception:
    nouns = ["ghost","storm","eagle","tiger","falcon","raven","cobra"]

uz_dict = []
try:
    uz_dict_path = os.path.join(os.path.dirname(__file__), 'uz_words_latin.txt')
    with open(uz_dict_path, 'r', encoding='utf-8') as f:
        uz_dict = [w.strip() for w in f if w.strip().isalpha() and 5 <= len(w.strip()) <= 12]
except Exception:
    uz_dict = UZ_WORDS_CLEAN

# ════════════════════════════════════════════════════════
#  GENERATOR
# ════════════════════════════════════════════════════════
def generate_quality_username(lang: str = None) -> str:
    if lang == 'uz':
        cat = random.choices(
            ["uz_male","uz_female","uz_word","uz_surname"],
            weights=[35, 20, 35, 10], k=1
        )[0]
    elif lang == 'en':
        cat = random.choices(
            ["en_male","en_female","animal","cool","nature","dict"],
            weights=[20, 10, 30, 20, 10, 10], k=1
        )[0]
    else:
        cat = random.choices(
            ["uz_male","uz_word","en_male","animal","cool","nature","dict"],
            weights=[15, 15, 15, 25, 15, 10, 5], k=1
        )[0]

    if cat == "uz_male":
        pool = [n for n in UZ_MALE_NAMES if n.isalpha() and 5 <= len(n) <= 8]
    elif cat == "uz_female":
        pool = [n for n in UZ_FEMALE_NAMES if n.isalpha() and 5 <= len(n) <= 8]
    elif cat == "uz_surname":
        pool = [n for n in UZ_SURNAMES if n.isalpha() and 5 <= len(n) <= 8]
    elif cat == "uz_word":
        pool = UZ_WORDS_CLEAN
    elif cat == "en_male":
        pool = [n for n in EN_MALE_NAMES if n.isalpha() and 5 <= len(n) <= 8]
    elif cat == "en_female":
        pool = [n for n in EN_FEMALE_NAMES if n.isalpha() and 5 <= len(n) <= 8]
    elif cat == "animal":
        pool = ANIMALS_CLEAN
    elif cat == "cool":
        pool = EN_COOL_CLEAN
    elif cat == "nature":
        pool = NATURE_CLEAN
    elif cat == "dict":
        pool = nouns[:5000] if nouns else EN_COOL_CLEAN
    else:
        pool = EN_COOL_CLEAN

    return random.choice(pool) if pool else "falcon"

def generate_smart_username(lang: str = None) -> str:
    return generate_quality_username(lang=lang)

# Legacy
UZ_PREFIXES = []
UZ_SUFFIXES = []
EN_PREFIXES = []
EN_NUMBERS = []
CATEGORIES = {"animals": ANIMALS_CLEAN[:10], "nature": NATURE_CLEAN[:10]}

def get_base_words():
    return EN_COOL_CLEAN[:20]

base_words = get_base_words()
