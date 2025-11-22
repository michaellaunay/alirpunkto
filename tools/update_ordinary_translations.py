#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def po_line(text: str, append_newline: bool = True) -> str:
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
    )
    if append_newline:
        return f'"{escaped}\\n"\n'
    return f'"{escaped}"\n'


translations = {
    "be": {
        "cooperator_heading": "<h2>Калі ласка, прадставіце інфармацыю, неабходную, каб зарэгістраваць вас як Супрацоўніка</h2>",
        "cooperator_notice": "<p><b>Важнае паведамленне:</b> У рэдкіх выпадках можа здарыцца, што форма ніжэй адлюстроўваецца няправільна: яна не пакажа, дзе ўвесці ваш псеўданім, ваш электронны адрас будзе можна змяняць... Калі так адбудзецца, проста націсніце кнопку \"Адправіць\" ніжэй. Форма, што адкрыецца, будзе правільнай, і вы зможаце яе без праблем запоўніць.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Калі ласка, прадставіце інфармацыю, неабходную, каб зарэгістраваць вас як Звычайнага члена супольнасці</h2>",
            "<p>Як Звычайны чалец супольнасці ${domain_name}, вы будзеце ўзаемадзейнічаць з іншымі яе членамі і з нашай ІТ-платформай.</p>",
            "<p>Каб гэта працавала найбольш эфектыўна і з павагай да вас і іншых членаў супольнасці, мы будзем удзячныя, калі вы прадставіце інфармацыю, запытаную ў форме ніжэй.</p>",
            "<p>Гэтыя даныя будуць выкарыстоўвацца выключна для кіравання вашым уліковым запісам як Звычайнага члена супольнасці ${domain_name}. Яны ніколі не будуць паказаныя іншым карыстальнікам ІТ-платформы ${domain_name} і не будуць перададзеныя або прададзеныя каму-небудзь, акрамя як для выканання юрыдычных патрабаванняў дзяржаўных органаў прымусу па запыце суддзі. \"Кантралёр даных\", як вызначана ў <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Агульным рэгламенце аб абароне даных (GDPR) Еўрапейскага Саюза</a>, — гэта CosmoPolitical Cooperative SCE, еўрапейскае кааператыўнае таварыства, размешчанае па адрасе 229 rue Solférino, 59000 Ліль, Францыя, зарэгістраванае 25 красавіка 2023 года пад нумарам SIREN 951 007 897.</p>",
            "<p><b>Важнае паведамленне:</b> У рэдкіх выпадках можа здарыцца, што форма ніжэй адлюстроўваецца няправільна: яна не пакажа, дзе ўвесці ваш псеўданім, ваш электронны адрас будзе можна змяняць... Калі так адбудзецца, проста націсніце кнопку \"Адправіць\" ніжэй. Форма, што адкрыецца, будзе правільнай, і вы зможаце яе без праблем запоўніць.</p>",
            "</div>",
        ],
    },
    "bg": {
        "cooperator_heading": "<h2>Моля, предоставете информацията, която ни е необходима, за да ви регистрираме като Кооператор</h2>",
        "cooperator_notice": "<p><b>Важно съобщение:</b> В редки случаи е възможно формулярът по-долу да не се визуализира правилно: той няма да ви покаже къде да въведете вашия псевдоним, вашият имейл адрес ще може да бъде редактиран... Ако това се случи, просто щракнете върху бутона \"Изпращане\" по-долу. Формулярът, който ще се появи, ще бъде правилен и ще можете лесно да го попълните.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Моля, предоставете информацията, която ни е необходима, за да ви регистрираме като Обикновен член на Общността</h2>",
            "<p>Като Обикновен член на общността ${domain_name}, вие ще взаимодействате с останалите ѝ членове и с нашата ИТ платформа.</p>",
            "<p>За да работи това по възможно най-ефективния и уважителен начин както за вас, така и за другите членове на Общността, ще сме благодарни, ако предоставите информацията, поискана във формуляра по-долу.</p>",
            "<p>Тези данни ще бъдат използвани единствено, за да управляваме вашия акаунт като Обикновен член на общността ${domain_name}. Те никога няма да бъдат показвани на другите потребители на ИТ платформата на ${domain_name}, нито ще бъдат предавани или продавани на когото и да било, освен за изпълнение на законови изисквания от публичните правоохранителни органи по искане на съдия. \"Контролерът на данните\", както е определено в <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Общия регламент за защита на данните (GDPR) на Европейския съюз</a>, е CosmoPolitical Cooperative SCE, европейско кооперативно дружество, със седалище на адрес 229 rue Solférino, 59000 Лил, Франция, регистрирано на 25 април 2023 г. под номер SIREN 951 007 897.</p>",
            "<p><b>Важно съобщение:</b> В редки случаи е възможно формулярът по-долу да не се визуализира правилно: той няма да ви покаже къде да въведете вашия псевдоним, вашият имейл адрес ще може да бъде редактиран... Ако това се случи, просто щракнете върху бутона \"Изпращане\" по-долу. Формулярът, който ще се появи, ще бъде правилен и ще можете лесно да го попълните.</p>",
            "</div>",
        ],
    },
    "bs": {
        "cooperator_heading": "<h2>Molimo vas da nam dostavite informacije koje su nam potrebne da bismo vas registrovali kao Kooperanta</h2>",
        "cooperator_notice": "<p><b>Važno obavještenje:</b> U rijetkim slučajevima može se dogoditi da se obrazac ispod ne prikaže ispravno: neće vam pokazati gdje da unesete svoj pseudonim, a vaša e-mail adresa će biti izmjenjiva... Ako se to dogodi, samo kliknite na dugme \"Pošalji\" ispod. Obrazac koji će se pojaviti biće ispravan i moći ćete ga lako popuniti.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Molimo vas da nam dostavite informacije koje su nam potrebne da bismo vas registrovali kao Običnog člana Zajednice</h2>",
            "<p>Kao Obični član zajednice ${domain_name}, komuniciraćete s ostalim članovima i s našom IT platformom.</p>",
            "<p>Kako bi ovo funkcionisalo što efikasnije i uz puno poštovanje prema vama i drugim članovima Zajednice, bili bismo zahvalni ako biste dostavili informacije tražene u donjem obrascu.</p>",
            "<p>Ovi podaci će se koristiti isključivo da bismo upravljali vašim nalogom kao Običnog člana zajednice ${domain_name}. Nikada neće biti prikazani drugim korisnicima IT platforme ${domain_name}, niti će biti preneseni ili prodati bilo kome, osim radi ispunjavanja zakonskih zahtjeva javnih organa gonjenja na zahtjev sudije. \"Kontrolor podataka\", kako je definisano u <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Opštoj uredbi o zaštiti podataka (GDPR) Evropske unije</a>, jeste CosmoPolitical Cooperative SCE, evropsko kooperativno društvo sa sjedištem na 229 rue Solférino, 59000 Lille, Francuska, registrovano 25. aprila 2023. pod brojem SIREN 951 007 897.</p>",
            "<p><b>Važno obavještenje:</b> U rijetkim slučajevima može se dogoditi da se obrazac ispod ne prikaže ispravno: neće vam pokazati gdje da unesete svoj pseudonim, a vaša e-mail adresa će biti izmjenjiva... Ako se to dogodi, samo kliknite na dugme \"Pošalji\" ispod. Obrazac koji će se pojaviti biće ispravan i moći ćete ga lako popuniti.</p>",
            "</div>",
        ],
    },
    "cs": {
        "cooperator_heading": "<h2>Prosím poskytněte informace, které potřebujeme k registraci vás jako Kooperátora</h2>",
        "cooperator_notice": "<p><b>Důležité upozornění:</b> Ve vzácných případech se může stát, že se formulář níže nezobrazí správně: neukáže vám, kam zadat váš pseudonym, a vaše e-mailová adresa bude upravitelná... Pokud k tomu dojde, jednoduše klikněte na tlačítko \"Odeslat\" níže. Formulář, který se poté zobrazí, bude správný a snadno jej vyplníte.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Prosím poskytněte informace, které potřebujeme k registraci vás jako řádného člena komunity</h2>",
            "<p>Jako řádný člen komunity ${domain_name} budete komunikovat s ostatními členy a s naší IT platformou.</p>",
            "<p>Aby vše fungovalo co nejefektivněji a s respektem k vám i ostatním členům komunity, budeme rádi, když poskytnete informace požadované ve formuláři níže.</p>",
            "<p>Tyto údaje použijeme výhradně k tomu, abychom spravovali váš účet řádného člena komunity ${domain_name}. Nikdy nebudou zobrazeny ostatním uživatelům IT platformy ${domain_name}, ani nebudou nikomu předány či prodány, s výjimkou splnění zákonných požadavků orgánů veřejné moci na žádost soudce. \"Správcem údajů\" ve smyslu <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">obecného nařízení o ochraně osobních údajů (GDPR) Evropské unie</a> je CosmoPolitical Cooperative SCE, evropské družstevní společenství se sídlem na adrese 229 rue Solférino, 59000 Lille, Francie, registrované dne 25. dubna 2023 pod číslem SIREN 951 007 897.</p>",
            "<p><b>Důležité upozornění:</b> Ve vzácných případech se může stát, že se formulář níže nezobrazí správně: neukáže vám, kam zadat váš pseudonym, a vaše e-mailová adresa bude upravitelná... Pokud k tomu dojde, jednoduše klikněte na tlačítko \"Odeslat\" níže. Formulář, který se poté zobrazí, bude správný a snadno jej vyplníte.</p>",
            "</div>",
        ],
    },
    "da": {
        "cooperator_heading": "<h2>Angiv venligst de oplysninger, vi har brug for, for at registrere dig som Kooperant</h2>",
        "cooperator_notice": "<p><b>Vigtig meddelelse:</b> I sjældne tilfælde kan formularen herunder blive vist forkert: den viser ikke, hvor du angiver dit pseudonym, og din e-mailadresse kan være redigerbar... Hvis det sker, skal du blot klikke på knappen \"Indsend\" nedenfor. Den formular, der derefter vises, vil være korrekt, og du kan udfylde den uden problemer.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Angiv venligst de oplysninger, vi har brug for, for at registrere dig som ordinært medlem af fællesskabet</h2>",
            "<p>Som ordinært medlem af ${domain_name}-fællesskabet vil du interagere med de andre medlemmer og med vores IT-platform.</p>",
            "<p>For at dette kan fungere så effektivt og respektfuldt som muligt for dig og for de andre medlemmer af fællesskabet, vil vi være taknemmelige, hvis du giver de oplysninger, der efterspørges i formularen nedenfor.</p>",
            "<p>Disse data anvendes udelukkende til, at vi kan administrere din konto som ordinært medlem af ${domain_name}-fællesskabet. De bliver aldrig vist for andre brugere af IT-platformen ${domain_name}, og de bliver heller ikke videregivet eller solgt til nogen, medmindre det er nødvendigt for at opfylde lovmæssige krav fra offentlige retshåndhævende myndigheder efter ordre fra en dommer. \"Dataansvarlig\", som defineret i <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">EU's generelle forordning om databeskyttelse (GDPR)</a>, er CosmoPolitical Cooperative SCE, et europæisk andelsselskab med hjemsted på 229 rue Solférino, 59000 Lille, Frankrig, registreret den 25. april 2023 under nummeret SIREN 951 007 897.</p>",
            "<p><b>Vigtig meddelelse:</b> I sjældne tilfælde kan formularen herunder blive vist forkert: den viser ikke, hvor du angiver dit pseudonym, og din e-mailadresse kan være redigerbar... Hvis det sker, skal du blot klikke på knappen \"Indsend\" nedenfor. Den formular, der derefter vises, vil være korrekt, og du kan udfylde den uden problemer.</p>",
            "</div>",
        ],
    },
    "el": {
        "cooperator_heading": "<h2>Παρακαλούμε δώστε τα στοιχεία που χρειαζόμαστε για να σας καταχωρίσουμε ως Συνεταιριστή</h2>",
        "cooperator_notice": "<p><b>Σημαντική ειδοποίηση:</b> Σε σπάνιες περιπτώσεις η παρακάτω φόρμα μπορεί να μην εμφανιστεί σωστά: δεν θα σας δείχνει πού να δηλώσετε το ψευδώνυμό σας, η διεύθυνση email σας θα είναι επεξεργάσιμη... Αν συμβεί αυτό, απλώς κάντε κλικ στο κουμπί \"Υποβολή\" παρακάτω. Η φόρμα που θα εμφανιστεί θα είναι σωστή και θα μπορέσετε να τη συμπληρώσετε εύκολα.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Παρακαλούμε δώστε τα στοιχεία που χρειαζόμαστε για να σας καταχωρίσουμε ως Τακτικό μέλος της Κοινότητας</h2>",
            "<p>Ως τακτικό μέλος της κοινότητας ${domain_name}, θα αλληλεπιδράτε με τα υπόλοιπα μέλη και με την πλατφόρμα πληροφορικής μας.</p>",
            "<p>Για να λειτουργήσει αυτό με τον πιο αποτελεσματικό και με σεβασμό τρόπο για εσάς και για τα άλλα μέλη της Κοινότητας, θα εκτιμούσαμε αν παρείχατε τις πληροφορίες που ζητούνται στη φόρμα παρακάτω.</p>",
            "<p>Αυτά τα δεδομένα θα χρησιμοποιηθούν αποκλειστικά για τη διαχείριση του λογαριασμού σας ως τακτικού μέλους της κοινότητας ${domain_name}. Δεν θα εμφανιστούν ποτέ σε άλλους χρήστες της πλατφόρμας πληροφορικής του ${domain_name}, ούτε θα διαβιβαστούν ή θα πωληθούν σε κανέναν, εκτός αν απαιτείται για τη συμμόρφωση με νομικές απαιτήσεις των δημόσιων αρχών επιβολής του νόμου κατόπιν αιτήματος δικαστή. Ο \"υπεύθυνος επεξεργασίας\", όπως ορίζεται από τον <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Γενικό Κανονισμό για την Προστασία Δεδομένων (GDPR) της Ευρωπαϊκής Ένωσης</a>, είναι ο CosmoPolitical Cooperative SCE, ένας ευρωπαϊκός συνεταιρισμός με έδρα την οδό 229 rue Solférino, 59000 Λιλ, Γαλλία, ο οποίος καταχωρίστηκε στις 25 Απριλίου 2023 με αριθμό SIREN 951 007 897.</p>",
            "<p><b>Σημαντική ειδοποίηση:</b> Σε σπάνιες περιπτώσεις η παρακάτω φόρμα μπορεί να μην εμφανιστεί σωστά: δεν θα σας δείχνει πού να δηλώσετε το ψευδώνυμό σας, η διεύθυνση email σας θα είναι επεξεργάσιμη... Αν συμβεί αυτό, απλώς κάντε κλικ στο κουμπί \"Υποβολή\" παρακάτω. Η φόρμα που θα εμφανιστεί θα είναι σωστή και θα μπορέσετε να τη συμπληρώσετε εύκολα.</p>",
            "</div>",
        ],
    },
    "et": {
        "cooperator_heading": "<h2>Palun esitage andmed, mida vajame, et registreerida teid Kooperandina</h2>",
        "cooperator_notice": "<p><b>Tähtis teade:</b> Harvadel juhtudel ei pruugi allolev vorm korrektselt kuvatud olla: see ei näita, kuhu sisestada oma pseudonüümi, teie e-posti aadress võib olla muudetav... Kui see juhtub, klõpsake lihtsalt all olevat nuppu \"Saada\". Avanev vorm on õige ja saate selle hõlpsalt täita.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Palun esitage andmed, mida vajame, et registreerida teid kogukonna tavaliikmena</h2>",
            "<p>Kogukonna ${domain_name} tavaliikmena suhtlete teiste liikmete ja meie IT-platvormiga.</p>",
            "<p>Selleks et kõik toimiks võimalikult tõhusalt ja lugupidavalt nii teie kui ka teiste kogukonna liikmete suhtes, palume teil esitada allolevas vormis nõutud teave.</p>",
            "<p>Neid andmeid kasutatakse üksnes selleks, et hallata teie kontot kogukonna ${domain_name} tavaliikmena. Neid ei kuvata kunagi teistele ${domain_name} IT-platvormi kasutajatele ega edastata või müüda kellelegi, välja arvatud seadusest tulenevate nõuete täitmiseks avalike õiguskaitseorganite ees kohtu korraldusel. \"Andmetöötleja\", nagu seda määratleb <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Euroopa Liidu isikuandmete kaitse üldmäärus (GDPR)</a>, on CosmoPolitical Cooperative SCE, Euroopa ühistu, mis asub aadressil rue Solférino 229, 59000 Lille, Prantsusmaa, ja registreeriti 25. aprillil 2023 numbriga SIREN 951 007 897.</p>",
            "<p><b>Tähtis teade:</b> Harvadel juhtudel ei pruugi allolev vorm korrektselt kuvatud olla: see ei näita, kuhu sisestada oma pseudonüümi, teie e-posti aadress võib olla muudetav... Kui see juhtub, klõpsake lihtsalt all olevat nuppu \"Saada\". Avanev vorm on õige ja saate selle hõlpsalt täita.</p>",
            "</div>",
        ],
    },
    "fi": {
        "cooperator_heading": "<h2>Anna tiedot, joita tarvitsemme rekisteröidäksemme sinut Kooperantiksi</h2>",
        "cooperator_notice": "<p><b>Tärkeä huomautus:</b> Harvoissa tapauksissa alla oleva lomake ei ehkä näy oikein: se ei näytä, mihin kirjoitat salanimen, ja sähköpostiosoitteesi saattaa olla muokattavissa... Jos näin käy, napsauta vain alla olevaa \"Lähetä\"-painiketta. Lomake, joka avautuu, on oikea ja voit täyttää sen helposti.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Anna tiedot, joita tarvitsemme rekisteröidäksemme sinut yhteisön tavalliseksi jäseneksi</h2>",
            "<p>Yhteisön ${domain_name} tavallisena jäsenenä olet vuorovaikutuksessa muiden jäsenten ja IT-alustamme kanssa.</p>",
            "<p>Jotta tämä toimisi mahdollisimman tehokkaasti ja kunnioittavasti sinua ja muita yhteisön jäseniä kohtaan, arvostaisimme, jos toimittaisit alla pyydetyt tiedot.</p>",
            "<p>Näitä tietoja käytetään yksinomaan tilisi hallintaan ${domain_name}-yhteisön tavallisena jäsenenä. Niitä ei koskaan näytetä muille ${domain_name}:n IT-alustan käyttäjille, eikä niitä luovuteta tai myydä kenellekään, paitsi jos julkiset lainvalvontaviranomaiset sitä tuomarin määräyksestä lain mukaan edellyttävät. \"Rekisterinpitäjä\", sellaisena kuin se on määritelty <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Euroopan unionin yleisessä tietosuoja-asetuksessa (GDPR)</a>, on CosmoPolitical Cooperative SCE, eurooppalainen osuuskuntayhtiö, jonka kotipaikka on 229 rue Solférino, 59000 Lille, Ranska ja joka on rekisteröity 25. huhtikuuta 2023 numerolla SIREN 951 007 897.</p>",
            "<p><b>Tärkeä huomautus:</b> Harvoissa tapauksissa alla oleva lomake ei ehkä näy oikein: se ei näytä, mihin kirjoitat salanimen, ja sähköpostiosoitteesi saattaa olla muokattavissa... Jos näin käy, napsauta vain alla olevaa \"Lähetä\"-painiketta. Lomake, joka avautuu, on oikea ja voit täyttää sen helposti.</p>",
            "</div>",
        ],
    },
    "ga": {
        "cooperator_heading": "<h2>Tabhair na sonraí atá de dhíth orainn chun thú a chlárú mar Chomhoibritheoir</h2>",
        "cooperator_notice": "<p><b>Fógra tábhachtach:</b> Uaireanta is annamh nach dtaispeántar an fhoirm thíos i gceart: ní thaispeánfaidh sí duit cá háit do leasainm a chur isteach agus beidh do sheoladh ríomhphoist in-eadóirsithe... Má tharlaíonn sé sin, cliceáil ar an gcnaipe \"Seol isteach\" thíos. Beidh an fhoirm a bheidh le feiceáil ina dhiaidh sin ceart agus beidh tú in ann í a líonadh go héasca.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Tabhair na sonraí atá de dhíth orainn chun thú a chlárú mar ghnáthbhall den Chomhphobal</h2>",
            "<p>Mar ghnáthbhall de Chomhphobal ${domain_name}, beidh tú ag idirghníomhú leis na baill eile agus lenár n-ardán TF.</p>",
            "<p>D’fhonn go n-oibreodh sé seo ar an mbealach is éifeachtaí agus is measúla duit féin agus do bhaill eile an Chomhphobail, bheimis buíoch dá gcuirfeá ar fáil an t-eolas a iarrtar san fhoirm thíos.</p>",
            "<p>Úsáidfear na sonraí seo go heisiach chun do chuntas mar ghnáthbhall de Chomhphobal ${domain_name} a bhainistiú. Ní thaispeánfar iad riamh d’úsáideoirí eile d’ardán TF ${domain_name}, agus ní aistrófar ná díolfar iad le haon duine, ach amháin chun riachtanais dlíthiúla ó údaráis forfheidhmithe poiblí a chomhlíonadh ar iarratas breithimh. Is é CosmoPolitical Cooperative SCE, comhlacht comhoibritheach Eorpach lonnaithe ag 229 rue Solférino, 59000 Lille, an Fhrainc, agus cláraithe ar an 25 Aibreán 2023 faoin uimhir SIREN 951 007 897, an \"rialaitheoir sonraí\" mar a shainmhínítear sa <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Rialachán Ginearálta maidir le Cosaint Sonraí (GDPR) de chuid an Aontais Eorpaigh</a>.</p>",
            "<p><b>Fógra tábhachtach:</b> Uaireanta is annamh nach dtaispeántar an fhoirm thíos i gceart: ní thaispeánfaidh sí duit cá háit do leasainm a chur isteach agus beidh do sheoladh ríomhphoist in-eadóirsithe... Má tharlaíonn sé sin, cliceáil ar an gcnaipe \"Seol isteach\" thíos. Beidh an fhoirm a bheidh le feiceáil ina dhiaidh sin ceart agus beidh tú in ann í a líonadh go héasca.</p>",
            "</div>",
        ],
    },
    "hr": {
        "cooperator_heading": "<h2>Molimo dostavite informacije koje su nam potrebne kako bismo vas registrirali kao Kooperanta</h2>",
        "cooperator_notice": "<p><b>Važna napomena:</b> U rijetkim slučajevima može se dogoditi da se donji obrazac ne prikaže ispravno: neće vam pokazati gdje upisati svoj pseudonim, a vaša adresa e-pošte bit će uređiva. Ako se to dogodi, jednostavno kliknite na gumb \"Pošalji\" u nastavku. Obrazac koji će se otvoriti bit će ispravan i moći ćete ga bez poteškoća ispuniti.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Molimo dostavite informacije koje su nam potrebne kako bismo vas registrirali kao redovitog člana Zajednice</h2>",
            "<p>Kao redoviti član zajednice ${domain_name} komunicirat ćete s ostalim članovima i s našom IT platformom.</p>",
            "<p>Kako bi sve funkcioniralo što učinkovitije i s poštovanjem prema vama i drugim članovima Zajednice, zahvalni smo vam ako dostavite podatke zatražene u obrascu niže.</p>",
            "<p>Ovi će se podaci koristiti isključivo za upravljanje vašim računom kao redovitog člana zajednice ${domain_name}. Nikada neće biti prikazani drugim korisnicima IT platforme ${domain_name}, niti će biti proslijeđeni ili prodani bilo kome, osim radi ispunjavanja zakonskih zahtjeva tijela javne vlasti za provedbu zakona na zahtjev suca. \"Voditelj obrade podataka\", kako ga definira <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Opća uredba o zaštiti podataka (GDPR) Europske unije</a>, jest CosmoPolitical Cooperative SCE, europsko zadružno društvo sa sjedištem na adresi rue Solférino 229, 59000 Lille, Francuska, registrirano 25. travnja 2023. pod brojem SIREN 951 007 897.</p>",
            "<p><b>Važna napomena:</b> U rijetkim slučajevima može se dogoditi da se donji obrazac ne prikaže ispravno: neće vam pokazati gdje upisati svoj pseudonim, a vaša adresa e-pošte bit će uređiva. Ako se to dogodi, jednostavno kliknite na gumb \"Pošalji\" u nastavku. Obrazac koji će se otvoriti bit će ispravan i moći ćete ga bez poteškoća ispuniti.</p>",
            "</div>",
        ],
    },
    "hu": {
        "cooperator_heading": "<h2>Kérjük, adja meg azokat az adatokat, amelyekre szükségünk van, hogy Kooperátorként regisztrálhassuk</h2>",
        "cooperator_notice": "<p><b>Fontos tudnivaló:</b> Ritka esetben előfordulhat, hogy az alábbi űrlap nem jelenik meg megfelelően: nem fogja megmutatni, hová írja be az álnevét, és az e-mail-címe szerkeszthető lesz... Ha ez megtörténik, kattintson egyszerűen az alul található \"Elküldés\" gombra. A megjelenő űrlap helyes lesz, és könnyen ki tudja tölteni.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Kérjük, adja meg azokat az adatokat, amelyekre szükségünk van, hogy a Közösség rendes tagjaként regisztrálhassuk</h2>",
            "<p>A ${domain_name} közösség rendes tagjaként kapcsolatba fog lépni a többi taggal és az IT-platformunkkal.</p>",
            "<p>Annak érdekében, hogy ez a lehető leghatékonyabban és legnagyobb tisztelettel működjön az Ön és a közösség többi tagja számára, hálásak lennénk, ha megadná az alábbi űrlapban kért információkat.</p>",
            "<p>Ezeket az adatokat kizárólag arra használjuk, hogy kezeljük az Ön fiókját a ${domain_name} közösség rendes tagjaként. Soha nem jelennek meg a ${domain_name} IT-platform más felhasználói számára, és nem adjuk át vagy adjuk el őket senkinek, kivéve, ha ezt a törvény előírja a közfelügyeleti szervek számára bírói kérésre. Az \"adatkezelő\", ahogyan azt az <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Európai Unió általános adatvédelmi rendelete (GDPR)</a> meghatározza, a CosmoPolitical Cooperative SCE, egy európai szövetkezeti társaság, amelynek székhelye a 229 rue Solférino, 59000 Lille, Franciaország, és amelyet 2023. április 25-én jegyeztek be a SIREN 951 007 897 számon.</p>",
            "<p><b>Fontos tudnivaló:</b> Ritka esetben előfordulhat, hogy az alábbi űrlap nem jelenik meg megfelelően: nem fogja megmutatni, hová írja be az álnevét, és az e-mail-címe szerkeszthető lesz... Ha ez megtörténik, kattintson egyszerűen az alul található \"Elküldés\" gombra. A megjelenő űrlap helyes lesz, és könnyen ki tudja tölteni.</p>",
            "</div>",
        ],
    },
    "is": {
        "cooperator_heading": "<h2>Vinsamlegast gefðu þær upplýsingar sem við þurfum til að skrá þig sem Samvinnuaðila</h2>",
        "cooperator_notice": "<p><b>Mikilvæg tilkynning:</b> Í sjaldgæfum tilvikum getur gerst að formið hér fyrir neðan birtist ekki rétt: það sýnir ekki hvar þú skráir dulnefnið þitt og tölvupóstfangið þitt verður breytanlegt... Ef þetta gerist skaltu bara smella á hnappinn \"Senda\" hér að neðan. Formið sem birtist verður rétt og þú getur auðveldlega fyllt það út.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Vinsamlegast gefðu þær upplýsingar sem við þurfum til að skrá þig sem venjulegan meðlim samfélagsins</h2>",
            "<p>Sem venjulegur meðlimur ${domain_name}-samfélagsins munt þú hafa samskipti við aðra meðlimi og upplýsingatæknivettvanginn okkar.</p>",
            "<p>Til að þetta virki eins skilvirkt og virðingarfyllst og hægt er fyrir þig og aðra meðlimi samfélagsins værum við þakklát ef þú gætir veitt upplýsingarnar sem beðið er um í forminu hér að neðan.</p>",
            "<p>Þessa gögn notum við eingöngu til að stýra aðgangi þínum sem venjulegs meðlims í ${domain_name}-samfélaginu. Þau verða aldrei birt öðrum notendum ${domain_name} upplýsingatæknivettvangsins né framseld eða seld til neins, nema til að uppfylla lagalegar kröfur opinberra löggæsluyfirvalda samkvæmt beiðni dómara. \"Gagnastjórinn\", eins og hann er skilgreindur í <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">almennu persónuverndarreglugerð Evrópusambandsins (GDPR)</a>, er CosmoPolitical Cooperative SCE, evrópskt samvinnufélag með aðsetur að 229 rue Solférino, 59000 Lille, Frakklandi, skráð 25. apríl 2023 undir númerinu SIREN 951 007 897.</p>",
            "<p><b>Mikilvæg tilkynning:</b> Í sjaldgæfum tilvikum getur gerst að formið hér fyrir neðan birtist ekki rétt: það sýnir ekki hvar þú skráir dulnefnið þitt og tölvupóstfangið þitt verður breytanlegt... Ef þetta gerist skaltu bara smella á hnappinn \"Senda\" hér að neðan. Formið sem birtist verður rétt og þú getur auðveldlega fyllt það út.</p>",
            "</div>",
        ],
    },
    "lt": {
        "cooperator_heading": "<h2>Prašome pateikti informaciją, kurios mums reikia, kad užregistruotume jus kaip Kooperantą</h2>",
        "cooperator_notice": "<p><b>Svarbus pranešimas:</b> Retais atvejais žemiau esanti forma gali būti rodoma neteisingai: joje nebus nurodyta, kur įrašyti jūsų slapyvardį, jūsų el. pašto adresą bus galima redaguoti... Jei taip atsitiks, tiesiog spustelėkite toliau esantį mygtuką \"Pateikti\". Forma, kuri bus parodyta, bus teisinga ir galėsite ją lengvai užpildyti.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Prašome pateikti informaciją, kurios mums reikia, kad užregistruotume jus kaip bendruomenės eilinį narį</h2>",
            "<p>Kaip ${domain_name} bendruomenės eilinis narys jūs bendrausite su kitais nariais ir su mūsų IT platforma.</p>",
            "<p>Siekiant, kad viskas veiktų kuo efektyviau ir pagarbiau jums ir kitiems bendruomenės nariams, būtume dėkingi, jei pateiktumėte žemiau esančioje formoje prašomą informaciją.</p>",
            "<p>Šie duomenys bus naudojami tik jūsų paskyrai, kaip ${domain_name} bendruomenės eiliniam nariui, tvarkyti. Jie niekada nebus rodomi kitiems ${domain_name} IT platformos naudotojams ir nebus perduodami ar parduodami jokiam kitam asmeniui, išskyrus atvejus, kai reikia įvykdyti teisėtus reikalavimus viešosioms teisėsaugos institucijoms teisėjo prašymu. \"Duomenų valdytojas\", kaip jis apibrėžtas <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Europos Sąjungos Bendrajame duomenų apsaugos reglamente (BDAR)</a>, yra CosmoPolitical Cooperative SCE, Europos kooperatinė bendrovė, įsikūrusi adresu 229 rue Solférino, 59000 Lilis, Prancūzija, įregistruota 2023 m. balandžio 25 d. numeriu SIREN 951 007 897.</p>",
            "<p><b>Svarbus pranešimas:</b> Retais atvejais žemiau esanti forma gali būti rodoma neteisingai: joje nebus nurodyta, kur įrašyti jūsų slapyvardį, jūsų el. pašto adresą bus galima redaguoti... Jei taip atsitiks, tiesiog spustelėkite toliau esantį mygtuką \"Pateikti\". Forma, kuri bus parodyta, bus teisinga ir galėsite ją lengvai užpildyti.</p>",
            "</div>",
        ],
    },
    "lv": {
        "cooperator_heading": "<h2>Lūdzu, sniedziet informāciju, kas mums nepieciešama, lai reģistrētu jūs kā Kooperatoru</h2>",
        "cooperator_notice": "<p><b>Svarīgs paziņojums:</b> Retos gadījumos zemāk redzamā forma var netikt parādīta pareizi: tā nerādīs, kur ievadīt jūsu pseidonīmu, un jūsu e-pasta adrese būs rediģējama... Ja tas notiek, vienkārši noklikšķiniet uz pogas \"Iesniegt\" zemāk. Forma, kas parādīsies, būs pareiza, un jūs to varēsiet viegli aizpildīt.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Lūdzu, sniedziet informāciju, kas mums nepieciešama, lai reģistrētu jūs kā kopienas parasto dalībnieku</h2>",
            "<p>Kā kopienas ${domain_name} parasts dalībnieks jūs sadarbojaties ar citiem dalībniekiem un ar mūsu IT platformu.</p>",
            "<p>Lai tas darbotos iespējami efektīvi un ar cieņu pret jums un citiem kopienas dalībniekiem, būsim pateicīgi, ja sniegsiet informāciju, kas pieprasīta zemāk esošajā formā.</p>",
            "<p>Šie dati tiks izmantoti tikai jūsu konta pārvaldībai kā kopienas ${domain_name} parastajam dalībniekam. Tie nekad netiks rādīti citiem ${domain_name} IT platformas lietotājiem un netiks nodoti vai pārdoti nevienam, izņemot gadījumus, kad tas nepieciešams, lai izpildītu tiesiskās prasības, ko valsts tiesībsargājošās iestādes izvirza pēc tiesneša pieprasījuma. \"Datu pārzinis\", kā to definē <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Eiropas Savienības Vispārīgā datu aizsardzības regula (GDPR)</a>, ir CosmoPolitical Cooperative SCE, Eiropas kooperatīvā sabiedrība ar juridisko adresi 229 rue Solférino, 59000 Lille, Francija, reģistrēta 2023. gada 25. aprīlī ar numuru SIREN 951 007 897.</p>",
            "<p><b>Svarīgs paziņojums:</b> Retos gadījumos zemāk redzamā forma var netikt parādīta pareizi: tā nerādīs, kur ievadīt jūsu pseidonīmu, un jūsu e-pasta adrese būs rediģējama... Ja tas notiek, vienkārši noklikšķiniet uz pogas \"Iesniegt\" zemāk. Forma, kas parādīsies, būs pareiza, un jūs to varēsiet viegli aizpildīt.</p>",
            "</div>",
        ],
    },
    "mt": {
        "cooperator_heading": "<h2>Jekk jogħġbok ipprovdi l-informazzjoni li għandna bżonn biex nirreġistrawk bħala Kooperant</h2>",
        "cooperator_notice": "<p><b>Avviż importanti:</b> F’każijiet rari jista’ jiġri li l-formola hawn taħt ma tidhirx kif suppost: ma jurikx fejn tidħol il-psewdonimu tiegħek, u l-indirizz tal-email tiegħek jista’ jiġi modifikat... Jekk jiġri dan, sempliċement ikklikkja l-buttuna \"Ibgħat\" hawn taħt. Il-formola li tidher wara tkun korretta u tkun tista’ timlaha mingħajr problemi.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Jekk jogħġbok ipprovdi l-informazzjoni li għandna bżonn biex nirreġistrawk bħala Membru Ordinarju tal-Komunità</h2>",
            "<p>Bħala Membru Ordinarju tal-komunità ${domain_name}, ser tinteraġixxi mal-membri l-oħra u mal-pjattaforma IT tagħna.</p>",
            "<p>Biex dan jaħdem bl-aktar mod effiċjenti u rispettus lejn tiegħek u lejn il-membri l-oħra tal-Komunità, inkunu grati jekk tipprovdi l-informazzjoni mitluba fil-formola hawn taħt.</p>",
            "<p>Dawn id-dejta jintużaw esklussivament biex inħaddmu l-kont tiegħek bħala Membru Ordinarju tal-komunità ${domain_name}. Qatt ma jidhru lill-utenti l-oħra tal-pjattaforma IT ta’ ${domain_name}, u lanqas ma jiġu trasmessi jew mibjugħa lil ħadd, ħlief biex jiġu ssodisfati rekwiżiti legali minn awtoritajiet pubbliċi tal-infurzar tal-liġi fuq talba ta’ imħallef. Il-\"kontrollur tad-dejta\", kif definit fir-<a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Regolament Ġenerali dwar il-Protezzjoni tad-Data (GDPR) tal-Unjoni Ewropea</a>, huwa CosmoPolitical Cooperative SCE, soċjetà kooperattiva Ewropea li tinsab 229 rue Solférino, 59000 Lille, Franza, u rreġistrata fit-25 ta’ April 2023 bin-numru SIREN 951 007 897.</p>",
            "<p><b>Avviż importanti:</b> F’każijiet rari jista’ jiġri li l-formola hawn taħt ma tidhirx kif suppost: ma jurikx fejn tidħol il-psewdonimu tiegħek, u l-indirizz tal-email tiegħek jista’ jiġi modifikat... Jekk jiġri dan, sempliċement ikklikkja l-buttuna \"Ibgħat\" hawn taħt. Il-formola li tidher wara tkun korretta u tkun tista’ timlaha mingħajr problemi.</p>",
            "</div>",
        ],
    },
    "no": {
        "cooperator_heading": "<h2>Vennligst oppgi informasjonen vi trenger for å registrere deg som Kooperant</h2>",
        "cooperator_notice": "<p><b>Viktig melding:</b> I sjeldne tilfeller kan skjemaet nedenfor vises feil: det viser ikke hvor du skal legge inn pseudonymet ditt, og e-postadressen din kan være redigerbar... Hvis det skjer, klikker du bare på knappen \"Send\" nedenfor. Skjemaet som da vises, vil være korrekt, og du kan enkelt fylle det ut.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Vennligst oppgi informasjonen vi trenger for å registrere deg som ordinært medlem av fellesskapet</h2>",
            "<p>Som ordinært medlem av ${domain_name}-fellesskapet vil du samhandle med de andre medlemmene og med vår IT-plattform.</p>",
            "<p>For at dette skal fungere så effektivt og respektfullt som mulig for deg og de andre medlemmene i fellesskapet, setter vi pris på at du gir informasjonen som etterspørres i skjemaet nedenfor.</p>",
            "<p>Disse dataene brukes utelukkende til å administrere kontoen din som ordinært medlem av ${domain_name}-fellesskapet. De vil aldri bli vist for andre brukere av IT-plattformen til ${domain_name}, og de vil ikke bli delt eller solgt til noen, bortsett fra når det er nødvendig for å oppfylle juridiske krav fra offentlige rettshåndhevende myndigheter etter pålegg fra en dommer. \"Behandlingsansvarlig\", slik den er definert i <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">EUs personvernforordning (GDPR)</a>, er CosmoPolitical Cooperative SCE, et europeisk samvirkeforetak med adresse 229 rue Solférino, 59000 Lille, Frankrike, registrert 25. april 2023 under nummeret SIREN 951 007 897.</p>",
            "<p><b>Viktig melding:</b> I sjeldne tilfeller kan skjemaet nedenfor vises feil: det viser ikke hvor du skal legge inn pseudonymet ditt, og e-postadressen din kan være redigerbar... Hvis det skjer, klikker du bare på knappen \"Send\" nedenfor. Skjemaet som da vises, vil være korrekt, og du kan enkelt fylle det ut.</p>",
            "</div>",
        ],
    },
    "pt": {
        "cooperator_heading": "<h2>Forneça, por favor, a informação de que precisamos para o registar como Cooperador</h2>",
        "cooperator_notice": "<p><b>Aviso importante:</b> Em casos raros, o formulário abaixo pode não ser apresentado corretamente: não mostrará onde indicar o seu pseudónimo e o seu endereço de e-mail poderá ser editável... Se isso acontecer, basta clicar no botão \"Submeter\" abaixo. O formulário que aparecerá em seguida estará correto e poderá preenchê-lo facilmente.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Forneça, por favor, a informação de que precisamos para o registar como Membro Ordinário da Comunidade</h2>",
            "<p>Como Membro Ordinário da comunidade ${domain_name}, irá interagir com os outros membros e com a nossa plataforma informática.</p>",
            "<p>Para que isto funcione da forma mais eficiente e respeitosa possível para si e para os restantes membros da Comunidade, agradecemos que forneça a informação solicitada no formulário abaixo.</p>",
            "<p>Estes dados serão utilizados exclusivamente para gerirmos a sua conta enquanto Membro Ordinário da comunidade ${domain_name}. Nunca serão mostrados a outros utilizadores da plataforma informática de ${domain_name}, nem serão transmitidos ou vendidos a terceiros, exceto para cumprir requisitos legais impostos por autoridades públicas de aplicação da lei a pedido de um juiz. O \"responsável pelo tratamento\", tal como definido pelo <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Regulamento Geral sobre a Proteção de Dados (RGPD) da União Europeia</a>, é a CosmoPolitical Cooperative SCE, uma sociedade cooperativa europeia com sede em 229 rue Solférino, 59000 Lille, França, registada em 25 de abril de 2023 com o número SIREN 951 007 897.</p>",
            "<p><b>Aviso importante:</b> Em casos raros, o formulário abaixo pode não ser apresentado corretamente: não mostrará onde indicar o seu pseudónimo e o seu endereço de e-mail poderá ser editável... Se isso acontecer, basta clicar no botão \"Submeter\" abaixo. O formulário que aparecerá em seguida estará correto e poderá preenchê-lo facilmente.</p>",
            "</div>",
        ],
    },
    "ro": {
        "cooperator_heading": "<h2>Vă rugăm să ne furnizați informațiile de care avem nevoie pentru a vă înregistra ca și Cooperator</h2>",
        "cooperator_notice": "<p><b>Avertisment important:</b> În cazuri rare, formularul de mai jos s-ar putea să nu se afișeze corect: nu vă va arăta unde să introduceți pseudonimul, iar adresa dumneavoastră de e-mail va fi editabilă... Dacă se întâmplă acest lucru, faceți clic pe butonul \"Trimite\" de mai jos. Formularul care va apărea va fi corect și îl veți putea completa cu ușurință.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Vă rugăm să ne furnizați informațiile de care avem nevoie pentru a vă înregistra ca Membru obișnuit al Comunității</h2>",
            "<p>În calitate de Membru obișnuit al comunității ${domain_name}, veți interacționa cu ceilalți membri și cu platforma noastră IT.</p>",
            "<p>Pentru ca acest lucru să funcționeze cât mai eficient și cu respect față de dumneavoastră și față de ceilalți membri ai Comunității, vă rugăm să oferiți informațiile solicitate în formularul de mai jos.</p>",
            "<p>Aceste date vor fi folosite exclusiv pentru a vă gestiona contul ca Membru obișnuit al comunității ${domain_name}. Ele nu vor fi niciodată afișate altor utilizatori ai platformei IT ${domain_name}, și nu vor fi transmise sau vândute nimănui, cu excepția îndeplinirii cerințelor legale formulate de autoritățile publice de aplicare a legii la cererea unui judecător. \"Operatorul de date\", așa cum este definit de <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Regulamentul general privind protecția datelor (GDPR) al Uniunii Europene</a>, este CosmoPolitical Cooperative SCE, o societate cooperativă europeană cu sediul la 229 rue Solférino, 59000 Lille, Franța, înregistrată la 25 aprilie 2023 cu numărul SIREN 951 007 897.</p>",
            "<p><b>Avertisment important:</b> În cazuri rare, formularul de mai jos s-ar putea să nu se afișeze corect: nu vă va arăta unde să introduceți pseudonimul, iar adresa dumneavoastră de e-mail va fi editabilă... Dacă se întâmplă acest lucru, faceți clic pe butonul \"Trimite\" de mai jos. Formularul care va apărea va fi corect și îl veți putea completa cu ușurință.</p>",
            "</div>",
        ],
    },
    "sk": {
        "cooperator_heading": "<h2>Prosím, uveďte informácie, ktoré potrebujeme na registráciu vás ako Kooperátora</h2>",
        "cooperator_notice": "<p><b>Dôležité upozornenie:</b> V ojedinelých prípadoch sa môže stať, že formulár nižšie sa nezobrazí správne: neukáže vám, kam zadať svoj pseudonym, a vaša e-mailová adresa bude upraviteľná... Ak k tomu dôjde, stačí kliknúť na tlačidlo \"Odoslať\" nižšie. Formulár, ktorý sa potom zobrazí, bude správny a jednoducho ho vyplníte.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Prosím, uveďte informácie, ktoré potrebujeme na registráciu vás ako riadneho člena komunity</h2>",
            "<p>Ako riadny člen komunity ${domain_name} budete komunikovať s ostatnými členmi a s našou IT platformou.</p>",
            "<p>Aby to fungovalo čo najefektívnejšie a s rešpektom k vám i ostatným členom komunity, budeme vďační, ak poskytnete informácie požadované vo formulári nižšie.</p>",
            "<p>Tieto údaje sa použijú výlučne na spravovanie vášho účtu ako riadneho člena komunity ${domain_name}. Nikdy nebudú zobrazené ostatným používateľom IT platformy ${domain_name}, ani nebudú poskytnuté alebo predané nikomu, okrem prípadov, keď je to potrebné na splnenie zákonných požiadaviek orgánov verejnej moci na základe požiadavky sudcu. \"Prevádzkovateľom údajov\", ako ho definuje <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">všeobecné nariadenie o ochrane údajov (GDPR) Európskej únie</a>, je CosmoPolitical Cooperative SCE, európske družstevné spoločenstvo so sídlom na adrese rue Solférino 229, 59000 Lille, Francúzsko, zapísané 25. apríla 2023 pod číslom SIREN 951 007 897.</p>",
            "<p><b>Dôležité upozornenie:</b> V ojedinelých prípadoch sa môže stať, že formulár nižšie sa nezobrazí správne: neukáže vám, kam zadať svoj pseudonym, a vaša e-mailová adresa bude upraviteľná... Ak k tomu dôjde, stačí kliknúť na tlačidlo \"Odoslať\" nižšie. Formulár, ktorý sa potom zobrazí, bude správny a jednoducho ho vyplníte.</p>",
            "</div>",
        ],
    },
    "sl": {
        "cooperator_heading": "<h2>Prosimo, navedite podatke, ki jih potrebujemo, da vas registriramo kot Kooperatorja</h2>",
        "cooperator_notice": "<p><b>Pomembno obvestilo:</b> V redkih primerih se lahko zgodi, da se spodnji obrazec ne prikaže pravilno: ne bo vam pokazal, kam vpisati svoj psevdonim, in vaš e-poštni naslov bo mogoče urediti... Če se to zgodi, preprosto kliknite na gumb \"Pošlji\" spodaj. Obrazec, ki se nato odpre, bo pravilen in ga boste lahko brez težav izpolnili.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Prosimo, navedite podatke, ki jih potrebujemo, da vas registriramo kot rednega člana skupnosti</h2>",
            "<p>Kot redni član skupnosti ${domain_name} boste sodelovali z drugimi člani in z našo IT-platformo.</p>",
            "<p>Da bo vse potekalo kar se da učinkovito in spoštljivo do vas in do drugih članov skupnosti, vas prosimo, da v spodnjem obrazcu zagotovite zahtevane informacije.</p>",
            "<p>Te podatke bomo uporabili izključno za upravljanje vašega računa kot rednega člana skupnosti ${domain_name}. Nikoli ne bodo prikazani drugim uporabnikom IT-platforme ${domain_name}, niti ne bodo posredovani ali prodani komurkoli, razen če je to potrebno za izpolnitev zakonskih zahtev javnih organov pregona na zahtevo sodnika. \"Upravljavec podatkov\", kot je opredeljen v <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">splošni uredbi o varstvu podatkov (GDPR) Evropske unije</a>, je CosmoPolitical Cooperative SCE, evropska zadruga s sedežem na naslovu rue Solférino 229, 59000 Lille, Francija, registrirana 25. aprila 2023 pod številko SIREN 951 007 897.</p>",
            "<p><b>Pomembno obvestilo:</b> V redkih primerih se lahko zgodi, da se spodnji obrazec ne prikaže pravilno: ne bo vam pokazal, kam vpisati svoj psevdonim, in vaš e-poštni naslov bo mogoče urediti... Če se to zgodi, preprosto kliknite na gumb \"Pošlji\" spodaj. Obrazec, ki se nato odpre, bo pravilen in ga boste lahko brez težav izpolnili.</p>",
            "</div>",
        ],
    },
    "sq": {
        "cooperator_heading": "<h2>Ju lutemi jepni informacionet që na duhen për t’ju regjistruar si Bashkëpunëtor</h2>",
        "cooperator_notice": "<p><b>Njoftim i rëndësishëm:</b> Në raste të rralla formulari më poshtë mund të mos shfaqet siç duhet: nuk do t’ju tregojë ku të vendosni pseudonimin tuaj dhe adresa juaj e email-it do të jetë e redaktueshme... Nëse kjo ndodh, thjesht klikoni butonin \"Dërgo\" më poshtë. Formulari që do të shfaqet do të jetë i saktë dhe do të mund ta plotësoni lehtësisht.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Ju lutemi jepni informacionet që na duhen për t’ju regjistruar si Anëtar i Rregullt i Komunitetit</h2>",
            "<p>Si Anëtar i Rregullt i komunitetit ${domain_name}, do të bashkëveproni me anëtarët e tjerë dhe me platformën tonë IT.</p>",
            "<p>Për ta bërë këtë sa më të efektshëm dhe respektues për ju dhe për anëtarët e tjerë të Komunitetit, do të ishim mirënjohës nëse do të jepnit informacionet e kërkuara në formularin më poshtë.</p>",
            "<p>Këto të dhëna do të përdoren vetëm për të administruar llogarinë tuaj si Anëtar i Rregullt i komunitetit ${domain_name}. Ato nuk do t’u shfaqen kurrë përdoruesve të tjerë të platformës IT të ${domain_name}, dhe nuk do t’u transmetohen apo shiten askujt, përveç rasteve kur kërkohet të plotësohen kërkesat ligjore të autoriteteve publike të zbatimit të ligjit me urdhër gjyqtari. \"Kontrolluesi i të dhënave\", siç përcaktohet nga <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Rregullorja e Përgjithshme për Mbrojtjen e të Dhënave (GDPR) e Bashkimit Evropian</a>, është CosmoPolitical Cooperative SCE, një shoqëri kooperative evropiane me seli në 229 rue Solférino, 59000 Lille, Francë, e regjistruar më 25 prill 2023 me numrin SIREN 951 007 897.</p>",
            "<p><b>Njoftim i rëndësishëm:</b> Në raste të rralla formulari më poshtë mund të mos shfaqet siç duhet: nuk do t’ju tregojë ku të vendosni pseudonimin tuaj dhe adresa juaj e email-it do të jetë e redaktueshme... Nëse kjo ndodh, thjesht klikoni butonin \"Dërgo\" më poshtë. Formulari që do të shfaqet do të jetë i saktë dhe do të mund ta plotësoni lehtësisht.</p>",
            "</div>",
        ],
    },
    "sr": {
        "cooperator_heading": "<h2>Molimo vas da nam dostavite informacije koje su nam potrebne da bismo vas registrovali kao Kooperatora</h2>",
        "cooperator_notice": "<p><b>Važna napomena:</b> U retkim slučajevima može se desiti da obrazac ispod ne prikaže ispravno: neće vam pokazati gde da unesete svoj pseudonim, a vaša imejl adresa biće izmenljiva... Ako se to desi, samo kliknite na dugme \\\"Pošalji\\\" ispod. Obrazac koji se zatim pojavi biće ispravan i moći ćete lako da ga popunite.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Molimo vas da nam dostavite informacije koje su nam potrebne da bismo vas registrovali kao Redovnog člana Zajednice</h2>",
            "<p>Kao Redovni član zajednice ${domain_name}, komuniciraćete sa ostalim članovima i sa našom IT platformom.</p>",
            "<p>Kako bi sve funkcionisalo što efikasnije i uz puno poštovanje prema vama i ostalim članovima Zajednice, bićemo vam zahvalni ako dostavite informacije koje se traže u formularu ispod.</p>",
            "<p>Ovi podaci će se koristiti isključivo da upravljamo vašim nalogom kao Redovnog člana zajednice ${domain_name}. Nikada neće biti prikazani drugim korisnicima IT platforme ${domain_name}, niti će biti prosleđeni ili prodati bilo kome, osim radi ispunjavanja zakonskih zahteva javnih organa gonjenja na zahtev sudije. \"Rukovalac podacima\", kako ga definiše <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Opšta uredba o zaštiti podataka (GDPR) Evropske unije</a>, jeste CosmoPolitical Cooperative SCE, evropsko zadružno društvo sa sedištem u ulici 229 rue Solférino, 59000 Lille, Francuska, registrovano 25. aprila 2023. pod brojem SIREN 951 007 897.</p>",
            "<p><b>Važna napomena:</b> U retkim slučajevima može se desiti da obrazac ispod ne prikaže ispravno: neće vam pokazati gde da unesete svoj pseudonim, a vaša imejl adresa biće izmenljiva... Ako se to desi, samo kliknite na dugme \\\"Pošalji\\\" ispod. Obrazac koji se zatim pojavi biće ispravan i moći ćete lako da ga popunite.</p>",
            "</div>",
        ],
    },
    "sv": {
        "cooperator_heading": "<h2>Lämna den information vi behöver för att registrera dig som Kooperatör</h2>",
        "cooperator_notice": "<p><b>Viktigt meddelande:</b> I sällsynta fall kan formuläret nedan visas felaktigt: det visar inte var du anger ditt pseudonym och din e-postadress kan gå att redigera... Om det händer klickar du bara på knappen \"Skicka\" nedan. Formuläret som visas kommer att vara korrekt och du kan enkelt fylla i det.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Lämna den information vi behöver för att registrera dig som ordinarie medlem i gemenskapen</h2>",
            "<p>Som ordinarie medlem i ${domain_name}-gemenskapen kommer du att interagera med de andra medlemmarna och med vår IT-plattform.</p>",
            "<p>För att detta ska fungera så effektivt och respektfullt som möjligt för dig och för de andra medlemmarna i gemenskapen uppskattar vi om du lämnar den information som efterfrågas i formuläret nedan.</p>",
            "<p>Dessa uppgifter används uteslutande för att vi ska kunna hantera ditt konto som ordinarie medlem i ${domain_name}-gemenskapen. De kommer aldrig att visas för andra användare av ${domain_name}s IT-plattform och kommer inte att överföras eller säljas till någon, förutom när det krävs för att uppfylla rättsliga krav från offentliga brottsbekämpande myndigheter på begäran av en domare. Den \"personuppgiftsansvarige\", enligt definitionen i <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">EU:s allmänna dataskyddsförordning (GDPR)</a>, är CosmoPolitical Cooperative SCE, ett europeiskt kooperativt bolag med säte på 229 rue Solférino, 59000 Lille, Frankrike, registrerat den 25 april 2023 med numret SIREN 951 007 897.</p>",
            "<p><b>Viktigt meddelande:</b> I sällsynta fall kan formuläret nedan visas felaktigt: det visar inte var du anger ditt pseudonym och din e-postadress kan gå att redigera... Om det händer klickar du bara på knappen \"Skicka\" nedan. Formuläret som visas kommer att vara korrekt och du kan enkelt fylla i det.</p>",
            "</div>",
        ],
    },
    "tr": {
        "cooperator_heading": "<h2>Lütfen Sizi Kooperatör olarak kaydetmemiz için gereken bilgileri sağlayın</h2>",
        "cooperator_notice": "<p><b>Önemli uyarı:</b> Nadir durumlarda aşağıdaki form doğru görüntülenmeyebilir: takma adınızı nereye yazacağınızı göstermeyebilir ve e-posta adresiniz düzenlenebilir durumda olabilir... Böyle bir şey olursa, aşağıdaki \"Gönder\" düğmesine tıklamanız yeterlidir. Açılacak form doğru olacaktır ve onu kolayca doldurabilirsiniz.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Lütfen Sizi Topluluğun Sıradan Üyesi olarak kaydetmemiz için gereken bilgileri sağlayın</h2>",
            "<p>${domain_name} topluluğunun Sıradan Üyesi olarak diğer üyeler ve BT platformumuz ile etkileşime gireceksiniz.</p>",
            "<p>Bu durumun sizin ve Topluluğun diğer üyelerinin yararına mümkün olduğunca verimli ve saygılı şekilde işlemesi için, aşağıdaki formda talep edilen bilgileri sağlamanızı rica ediyoruz.</p>",
            "<p>Bu veriler yalnızca ${domain_name} topluluğunun Sıradan Üyesi olarak hesabınızı yönetmemiz amacıyla kullanılacaktır. Hiçbir zaman ${domain_name} BT platformunun diğer kullanıcılarına gösterilmeyecek ve bir hâkimin talebi üzerine kamu kolluk makamlarının yasal gerekliliklerini yerine getirmek haricinde herhangi bir kişiye aktarılmayacak veya satılmayacaktır. Avrupa Birliği'nin <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Genel Veri Koruma Tüzüğü (GDPR)</a>nde tanımlanan \"veri sorumlusu\" 229 rue Solférino, 59000 Lille, Fransa adresinde bulunan ve 25 Nisan 2023 tarihinde SIREN 951 007 897 numarasıyla tescil edilen bir Avrupa Kooperatif Şirketi olan CosmoPolitical Cooperative SCE'dir.</p>",
            "<p><b>Önemli uyarı:</b> Nadir durumlarda aşağıdaki form doğru görüntülenmeyebilir: takma adınızı nereye yazacağınızı göstermeyebilir ve e-posta adresiniz düzenlenebilir durumda olabilir... Böyle bir şey olursa, aşağıdaki \"Gönder\" düğmesine tıklamanız yeterlidir. Açılacak form doğru olacaktır ve onu kolayca doldurabilirsiniz.</p>",
            "</div>",
        ],
    },
    "uk": {
        "cooperator_heading": "<h2>Будь ласка, надайте інформацію, яка потрібна нам, щоб зареєструвати вас як Кооператора</h2>",
        "cooperator_notice": "<p><b>Важливе повідомлення:</b> У поодиноких випадках наведена нижче форма може відображатися некоректно: вона не покаже, де вказати ваш псевдонім, а вашу адресу електронної пошти можна буде змінювати... Якщо це станеться, просто натисніть кнопку \"Надіслати\" нижче. Форма, яка з’явиться, буде правильною, і ви зможете легко її заповнити.</p>",
        "ordinary_lines": [
            "<div>",
            "<h2>Будь ласка, надайте інформацію, яка потрібна нам, щоб зареєструвати вас як Звичайного члена Спільноти</h2>",
            "<p>Як Звичайний член спільноти ${domain_name}, ви будете взаємодіяти з іншими учасниками та з нашою ІТ-платформою.</p>",
            "<p>Щоб усе працювало якомога ефективніше та з повагою до вас і до інших членів Спільноти, просимо надати інформацію, яку запитує форма нижче.</p>",
            "<p>Ці дані використовуватимуться виключно для керування вашим обліковим записом як Звичайного члена спільноти ${domain_name}. Вони ніколи не відображатимуться іншим користувачам ІТ-платформи ${domain_name} і не передаватимуться чи продаватимуться нікому, окрім випадків виконання правових вимог державних органів правопорядку за запитом судді. \"Володільцем даних\", як його визначено у <a href=\"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R0679-20160504\">Загальному регламенті Європейського Союзу із захисту даних (GDPR)</a>, є CosmoPolitical Cooperative SCE, європейське кооперативне товариство з офісом за адресою 229 rue Solférino, 59000 Лілль, Франція, зареєстроване 25 квітня 2023 року під номером SIREN 951 007 897.</p>",
            "<p><b>Важливе повідомлення:</b> У поодиноких випадках наведена нижче форма може відображатися некоректно: вона не покаже, де вказати ваш псевдонім, а вашу адресу електронної пошти можна буде змінювати... Якщо це станеться, просто натисніть кнопку \"Надіслати\" нижче. Форма, яка з’явиться, буде правильною, і ви зможете легко її заповнити.</p>",
            "</div>",
        ],
    },
}


def ensure_cooperator_heading(lines: list[str], lang: str, heading_line: str, notice_line: str) -> None:
    start = None
    for idx, line in enumerate(lines):
        if line.startswith('msgid "cooperator_data_explanation"'):
            start = idx
            break
    if start is None:
        raise ValueError(f"cooperator_data_explanation not found for {lang}")
    end = start + 1
    while end < len(lines) and not lines[end].startswith('msgid "'):
        end += 1
    entry_slice = lines[start:end]
    heading_po = po_line(heading_line)
    if heading_po not in entry_slice:
        for idx in range(start, end):
            if lines[idx].strip() == '"<div>\\n"':
                lines.insert(idx + 1, heading_po)
                break
    notice_po = po_line(notice_line)
    if notice_po not in entry_slice:
        for idx in range(end - 1, start, -1):
            if lines[idx].strip() == '"</div>"':
                lines.insert(idx, notice_po)
                break


def ensure_ordinary_entry(lines: list[str], lang: str, ordinary_lines: list[str]) -> None:
    has_entry = any(line.startswith('msgid "ordinary_member_data_explanation"') for line in lines)
    if has_entry:
        return
    entry_lines = ['msgid "ordinary_member_data_explanation"\n', 'msgstr ""\n']
    for idx, text in enumerate(ordinary_lines):
        entry_lines.append(po_line(text, idx != len(ordinary_lines) - 1))
    entry_lines.append("\n")
    insert_pos = None
    for idx, line in enumerate(lines):
        if line.startswith('msgid "human_verification_explanation"'):
            insert_pos = idx
            break
    if insert_pos is None:
        raise ValueError(f"human_verification_explanation not found for {lang}")
    for offset, line in enumerate(entry_lines):
        lines.insert(insert_pos + offset, line)


def main() -> None:
    for lang, data in translations.items():
        path = Path(f"locale/{lang}/LC_MESSAGES/alirpunkto.po")
        text = path.read_text()
        lines = text.splitlines(True)
        ensure_cooperator_heading(lines, lang, data["cooperator_heading"], data["cooperator_notice"])
        ensure_ordinary_entry(lines, lang, data["ordinary_lines"])
        path.write_text("".join(lines))


if __name__ == "__main__":
    main()
