"""Synthetic labelled training dataset (EN / RU / KZ) for the request classifier.

Each category has core "problem" phrases per language; samples are built by combining
openers + problem + optional context/closers so the model sees realistic free text.
Generation is deterministic (seeded) so evaluation numbers are reproducible.
"""
import random

CATEGORIES = [
    "Academic",
    "Registration & Enrollment",
    "Finance & Scholarships",
    "IT Support",
    "Dormitory & Housing",
    "Documents & Certificates",
    "Library",
    "Health & Wellbeing",
    "International Office",
    "Other",
]

PROBLEMS: dict[str, dict[str, list[str]]] = {
    "Academic": {
        "en": [
            "I want to appeal my final exam grade in calculus",
            "my grade for the midterm was entered incorrectly",
            "I need to retake the physics course I failed",
            "the professor has not published the grades for the course yet",
            "I disagree with the assessment of my course project",
            "can I get an academic leave for one semester",
            "I need permission to take the exam on another date",
            "my GPA was calculated wrong in the academic record",
            "how do I change my major to computer science",
            "I missed the exam because of a family emergency and need a makeup exam",
            "the teacher marked me absent although I attended the lecture",
            "question about my thesis supervisor and defense date",
            "I want to file a grade appeal for the database course",
            "the dean's office has not approved my individual study plan",
        ],
        "ru": [
            "хочу подать апелляцию на оценку за экзамен",
            "мне неправильно выставили оценку за рубежный контроль",
            "нужно пересдать предмет, который я завалил",
            "преподаватель до сих пор не выставил оценки",
            "не согласен с оценкой за курсовой проект",
            "хочу оформить академический отпуск на семестр",
            "прошу разрешить сдать экзамен в другой день",
            "неправильно посчитан мой GPA",
            "как перевестись на другую специальность",
            "пропустил экзамен по уважительной причине, нужна пересдача",
            "мне поставили пропуск, хотя я был на лекции",
            "вопрос по защите дипломной работы и научному руководителю",
            "деканат не утвердил мой индивидуальный учебный план",
        ],
        "kz": [
            "емтихан бағасына апелляция бергім келеді",
            "аралық бақылау бағам қате қойылған",
            "құлаған пәнді қайта тапсыруым керек",
            "оқытушы әлі бағаларды қоймады",
            "курстық жобаның бағасымен келіспеймін",
            "бір семестрге академиялық демалыс алғым келеді",
            "емтиханды басқа күні тапсыруға рұқсат сұраймын",
            "GPA қате есептелген",
            "басқа мамандыққа ауысу туралы сұрақ",
            "дәлелді себеппен емтиханды өткізіп алдым, қайта тапсыру керек",
            "дипломдық жұмысты қорғау күні туралы сұрақ",
            "деканат жеке оқу жоспарымды бекітпеді",
        ],
    },
    "Registration & Enrollment": {
        "en": [
            "I cannot register for the elective course",
            "the registration system does not let me add a course",
            "I need to drop a course after the add/drop deadline",
            "my enrollment status shows inactive",
            "the elective I need is full, can I be added to the waitlist",
            "I was not enrolled in the next semester automatically",
            "course registration shows a prerequisite error",
            "how do I register for summer semester courses",
            "I want to transfer credits from my previous university",
            "my course schedule has a time conflict after registration",
            "I need to re-enroll after academic leave",
            "registration for the minor program is not available for me",
        ],
        "ru": [
            "не могу записаться на элективный курс",
            "система регистрации не дает добавить дисциплину",
            "хочу отказаться от курса после окончания срока регистрации",
            "мой статус зачисления неактивный",
            "на нужный элективный курс нет мест",
            "меня не зачислили на следующий семестр",
            "при регистрации на курс ошибка пререквизита",
            "как зарегистрироваться на летний семестр",
            "хочу перезачесть кредиты из другого университета",
            "после регистрации накладка в расписании курсов",
            "нужно восстановиться после академического отпуска",
        ],
        "kz": [
            "элективті курсқа тіркеле алмаймын",
            "тіркеу жүйесі пәнді қосуға мүмкіндік бермейді",
            "тіркеу мерзімі өткеннен кейін курстан бас тартқым келеді",
            "оқуға қабылдану мәртебем белсенді емес",
            "қажетті элективті курста орын жоқ",
            "келесі семестрге тіркелмей қалдым",
            "пәнге тіркелу кезінде пререквизит қатесі шығады",
            "жазғы семестрге қалай тіркелуге болады",
            "басқа университеттен кредиттерді қайта есептегім келеді",
        ],
    },
    "Finance & Scholarships": {
        "en": [
            "my scholarship payment is delayed this month",
            "I paid the tuition but the payment is not reflected",
            "I cannot pay tuition online, the payment is blocked",
            "how can I apply for a tuition discount",
            "I was charged twice for the semester fee",
            "my stipend was not transferred to my bank card",
            "I need an installment plan for the tuition fee",
            "question about the scholarship application and its requirements",
            "I need a refund for the overpaid tuition",
            "the invoice for this semester shows the wrong amount",
            "when will the grant holders receive the monthly stipend",
            "I lost my scholarship and want to know why",
        ],
        "ru": [
            "задерживается выплата стипендии",
            "я оплатил обучение, но оплата не отображается",
            "не могу оплатить обучение онлайн",
            "как получить скидку на оплату обучения",
            "с меня дважды списали оплату за семестр",
            "стипендия не пришла на карту",
            "нужна рассрочка по оплате за обучение",
            "вопрос по заявке на стипендию",
            "прошу вернуть переплату за обучение",
            "в счете за семестр неправильная сумма",
            "меня лишили стипендии, хочу узнать причину",
        ],
        "kz": [
            "шәкіртақы төлеуі кешігіп жатыр",
            "оқу ақысын төледім, бірақ төлем көрінбейді",
            "оқу ақысын онлайн төлей алмаймын",
            "оқу ақысына жеңілдікті қалай алуға болады",
            "семестр ақысы екі рет алынды",
            "стипендия картаға түспеді",
            "оқу ақысын бөліп төлеу керек",
            "шәкіртақыға өтінім туралы сұрақ",
            "артық төленген ақшаны қайтаруды сұраймын",
        ],
    },
    "IT Support": {
        "en": [
            "I cannot log in to Moodle, password reset does not work",
            "my university email account is locked",
            "the campus Wi-Fi does not connect on my laptop",
            "I forgot my password for the student portal",
            "Microsoft Teams shows an error when I join the class",
            "the LMS page does not load and shows error 500",
            "I cannot access the exam system with my account",
            "two-factor authentication code is not arriving",
            "the computer in the lab does not turn on",
            "I need a license for Office 365 as a student",
            "my login and password are not accepted by the portal",
            "the VPN for remote access is not working",
            "the website crashes when I upload my assignment",
        ],
        "ru": [
            "не могу войти в Moodle, сброс пароля не работает",
            "заблокирована моя университетская почта",
            "Wi-Fi в кампусе не подключается",
            "забыл пароль от студенческого портала",
            "Teams выдает ошибку при входе на занятие",
            "страница LMS не загружается, ошибка 500",
            "не могу зайти в систему тестирования",
            "не приходит код двухфакторной аутентификации",
            "компьютер в лаборатории не включается",
            "логин и пароль не принимаются порталом",
            "не работает VPN для удаленного доступа",
            "сайт зависает при загрузке задания",
        ],
        "kz": [
            "Moodle-ге кіре алмаймын, құпиясөзді қалпына келтіру жұмыс істемейді",
            "университеттік поштам бұғатталды",
            "кампустағы Wi-Fi қосылмайды",
            "студенттік порталдың құпиясөзін ұмытып қалдым",
            "Teams сабаққа кірген кезде қате көрсетеді",
            "LMS беті ашылмайды",
            "тест жүйесіне кіре алмаймын",
            "логин мен құпиясөз қабылданбайды",
            "зертханадағы компьютер қосылмайды",
        ],
    },
    "Dormitory & Housing": {
        "en": [
            "the heating in my dormitory room is not working",
            "I have a conflict with my roommate and want to change rooms",
            "the shower in the dorm is broken for a week",
            "I need a place in the dormitory for next semester",
            "the window in my room does not close",
            "there are cockroaches in the dorm kitchen",
            "my dorm room door lock is broken",
            "no hot water in the dormitory building",
            "how to pay for the dormitory accommodation",
            "the internet cable in my dorm room was cut",
            "I want to move out of the dormitory early",
            "the electricity socket in my room sparks",
        ],
        "ru": [
            "в комнате общежития не работает отопление",
            "конфликт с соседом по комнате, хочу переселиться",
            "в общежитии неделю не работает душ",
            "нужно место в общежитии на следующий семестр",
            "окно в комнате не закрывается",
            "на кухне в общежитии тараканы",
            "сломан замок на двери моей комнаты",
            "в общежитии нет горячей воды",
            "как оплатить проживание в общежитии",
            "хочу досрочно выехать из общежития",
        ],
        "kz": [
            "жатақхана бөлмесінде жылу жоқ",
            "бөлмелесіммен келіспеушілік бар, бөлме ауыстырғым келеді",
            "жатақханада душ бір апта бойы істемейді",
            "келесі семестрге жатақханадан орын керек",
            "бөлмедегі терезе жабылмайды",
            "жатақханада ыстық су жоқ",
            "бөлме есігінің құлпы сынған",
            "жатақхана ақысын қалай төлеуге болады",
        ],
    },
    "Documents & Certificates": {
        "en": [
            "I need a transcript of records for my visa application",
            "please issue an enrollment certificate for the bank",
            "I need a certificate of study for the military office",
            "how long does it take to get an official transcript",
            "I need a copy of my diploma supplement",
            "please prepare a reference letter confirming I am a student",
            "I need an apostille on my transcript",
            "my student ID card was lost and I need a new one",
            "I need a certificate for the tax office that I study full time",
            "can I get my transcript in English",
            "I need a certified copy of my academic transcript for an employer",
            "request for a spravka confirming student status",
        ],
        "ru": [
            "нужна справка с места учебы для банка",
            "прошу выдать транскрипт для получения визы",
            "нужна справка для военкомата",
            "сколько делается официальный транскрипт",
            "нужна копия приложения к диплому",
            "потерял студенческий билет, нужен новый",
            "нужна справка о том, что я обучаюсь на очной форме",
            "можно получить транскрипт на английском языке",
            "нужна справка-подтверждение статуса студента",
            "заказать архивную справку",
        ],
        "kz": [
            "банкке оқу орнынан анықтама керек",
            "виза алу үшін транскрипт беруіңізді сұраймын",
            "әскери комиссариатқа анықтама керек",
            "ресми транскрипт қанша уақытта дайын болады",
            "диплом қосымшасының көшірмесі керек",
            "студенттік билетімді жоғалтып алдым, жаңасы керек",
            "күндізгі оқу туралы анықтама керек",
            "студент мәртебесін растайтын анықтама керек",
        ],
    },
    "Library": {
        "en": [
            "I want to extend the return date of a library book",
            "I cannot access the Scopus database from home",
            "how do I return a book if the library is closed",
            "I was fined for a late book return by mistake",
            "the e-library does not open the journal articles",
            "I need access to the Web of Science database",
            "can I reserve a study room in the library",
            "the library catalog shows the book available but it is not on the shelf",
            "I lost a library book, what should I do",
            "book return question about the overdue notice",
            "I need help finding sources for my thesis in the library",
        ],
        "ru": [
            "хочу продлить срок возврата книги в библиотеку",
            "не могу получить доступ к базе Scopus из дома",
            "как вернуть книгу, если библиотека закрыта",
            "мне ошибочно начислили штраф за просрочку книги",
            "электронная библиотека не открывает статьи",
            "можно забронировать читальный зал в библиотеке",
            "потерял библиотечную книгу, что делать",
            "нужна помощь с поиском литературы в библиотеке",
        ],
        "kz": [
            "кітапханадан алған кітаптың мерзімін ұзартқым келеді",
            "үйден Scopus базасына кіре алмаймын",
            "кітапхана жабық болса кітапты қалай қайтаруға болады",
            "кітапты кеш қайтарғаным үшін қате айыппұл салынды",
            "электронды кітапхана мақалаларды ашпайды",
            "кітапхана кітабын жоғалтып алдым",
        ],
    },
    "Health & Wellbeing": {
        "en": [
            "I feel unwell and need to see a doctor",
            "I need psychological support, I am very stressed",
            "I feel unsafe in my dorm room",
            "I have a high fever and cannot attend classes",
            "I need a medical certificate for missed classes",
            "I am experiencing anxiety and panic attacks before exams",
            "someone is harassing me on campus",
            "I injured my leg during the sports class",
            "I want to talk to a counsellor about depression",
            "I need to get vaccinated at the medical center",
            "I feel lonely and overwhelmed and need someone to talk to",
            "there was a safety incident in the building and I am scared",
        ],
        "ru": [
            "плохо себя чувствую, нужен врач",
            "нужна психологическая помощь, сильный стресс",
            "чувствую себя небезопасно в общежитии",
            "у меня высокая температура, не могу прийти на занятия",
            "нужна медицинская справка о болезни",
            "панические атаки и тревога перед экзаменами",
            "меня преследуют и домогаются в университете",
            "получил травму на физкультуре",
            "хочу поговорить с психологом о депрессии",
        ],
        "kz": [
            "өзімді жаман сезінемін, дәрігер керек",
            "психологиялық көмек керек, қатты күйзеліс",
            "жатақханада өзімді қауіпсіз сезінбеймін",
            "қызуым көтерілді, сабаққа келе алмаймын",
            "ауырғаным туралы медициналық анықтама керек",
            "емтихан алдында үрей мен дүрбелең",
            "психологпен сөйлескім келеді",
        ],
    },
    "International Office": {
        "en": [
            "I need help with my student visa extension",
            "how can I apply for the exchange program in Europe",
            "my migration registration expires next week",
            "I am an international student and need an invitation letter",
            "question about the Erasmus mobility program",
            "I need a visa support letter for my parents",
            "how do I get a residence permit as a foreign student",
            "can I do a semester abroad at a partner university",
            "I need to register with the migration police",
            "the deadline for the academic mobility program application",
        ],
        "ru": [
            "нужна помощь с продлением студенческой визы",
            "как подать заявку на программу обмена",
            "заканчивается миграционная регистрация",
            "я иностранный студент, нужно приглашение",
            "вопрос по программе Erasmus",
            "как получить вид на жительство иностранному студенту",
            "хочу семестр учиться в университете-партнере за границей",
            "программа академической мобильности, сроки подачи",
            "хочу поехать по обмену в зарубежный университет",
            "подать документы на обмен на весенний семестр",
        ],
        "kz": [
            "студенттік визаны ұзартуға көмек керек",
            "алмасу бағдарламасына қалай өтінім беруге болады",
            "көші-қон тіркеуім аяқталып жатыр",
            "шетелдік студентпін, шақыру хат керек",
            "академиялық ұтқырлық бағдарламасы туралы сұрақ",
            "серіктес университетте бір семестр оқығым келеді",
        ],
    },
    "Other": {
        "en": [
            "help please",
            "I have a question",
            "hello, I need some information",
            "where can I find the lost and found",
            "I want to give feedback about the canteen food",
            "can I bring a guest to the campus event",
            "how do I join a student club",
            "what are the opening hours of the sports center",
            "I have a suggestion for the university",
            "who should I contact about parking on campus",
        ],
        "ru": [
            "помогите пожалуйста",
            "у меня вопрос",
            "где находится бюро находок",
            "хочу оставить отзыв о столовой",
            "как вступить в студенческий клуб",
            "какие часы работы спортзала",
            "у меня есть предложение для университета",
        ],
        "kz": [
            "көмектесіңізші",
            "менің сұрағым бар",
            "жоғалған заттар бюросы қайда",
            "асхана туралы пікір қалдырғым келеді",
            "студенттік клубқа қалай кіруге болады",
            "спорт залының жұмыс уақыты қандай",
        ],
    },
}

OPENERS = {
    "en": ["", "Hello, ", "Hi, ", "Good afternoon. ", "Dear support, ", "Please help: ", "Hello! "],
    "ru": ["", "Здравствуйте, ", "Добрый день. ", "Помогите, ", "Привет, ", "Уважаемая поддержка, "],
    "kz": ["", "Сәлеметсіз бе, ", "Қайырлы күн. ", "Көмектесіңіз, ", "Сәлем, "],
}

CLOSERS = {
    "en": ["", ".", " Thank you.", " Please help as soon as possible.", " What should I do?", " Thanks in advance."],
    "ru": ["", ".", " Спасибо.", " Подскажите, что делать?", " Помогите как можно скорее."],
    "kz": ["", ".", " Рахмет.", " Не істеу керек?", " Тезірек көмектесіңізші."],
}

CONTEXTS = {
    "en": ["", " I am a second year student.", " This is the second time it happens.", " It started yesterday."],
    "ru": ["", " Я студент второго курса.", " Это уже второй раз.", " Началось вчера."],
    "kz": ["", " Мен екінші курс студентімін.", " Бұл екінші рет болып тұр.", " Кеше басталды."],
}


def _variant(rng: random.Random, lang: str, problem: str) -> str:
    return rng.choice(OPENERS[lang]) + problem + rng.choice(CONTEXTS[lang]) + rng.choice(CLOSERS[lang])


def generate(per_phrase: int = 3, min_per_category: int = 70, seed: int = 42) -> list[tuple[str, str]]:
    """Every core phrase appears in `per_phrase` variants; categories are topped up to `min_per_category`."""
    rng = random.Random(seed)
    data: list[tuple[str, str]] = []
    for cat, by_lang in PROBLEMS.items():
        seen: set[str] = set()
        rows: list[str] = []
        for lang, problems in by_lang.items():
            for problem in problems:
                for _ in range(per_phrase * 4):
                    if sum(problem in r for r in rows) >= per_phrase:
                        break
                    text = _variant(rng, lang, problem)
                    if text not in seen:
                        seen.add(text)
                        rows.append(text)
        attempts = 0
        while len(rows) < min_per_category and attempts < min_per_category * 20:
            attempts += 1
            lang = rng.choice(list(by_lang))
            text = _variant(rng, lang, rng.choice(by_lang[lang]))
            if cat != "Other":
                # Two problems of the same category in one message.
                text += " " + rng.choice(by_lang[lang])
            if text not in seen:
                seen.add(text)
                rows.append(text)
        data += [(t, cat) for t in rows]
    rng.shuffle(data)
    return data


def sample_subject(cat: str, rng: random.Random) -> tuple[str, str]:
    """Return (subject, description) pair for seeding demo requests."""
    lang = rng.choice(["en", "en", "en", "ru", "kz"])
    problem = rng.choice(PROBLEMS[cat][lang])
    subject = problem[:1].upper() + problem[1:]
    subject = subject if len(subject) <= 70 else subject[:67] + "..."
    description = rng.choice(OPENERS[lang]) + problem + rng.choice(CONTEXTS[lang]) + rng.choice(CLOSERS[lang])
    return subject, description
