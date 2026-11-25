import type { Lang } from "./types";

/** Public copy and illustrative routing examples in KZ, RU and EN. */
export interface LandingCopy {
  nav: { how: string; offices: string; sla: string; faq: string; signIn: string; openPortal: string; skip: string };
  hero: { title1: string; title2: string; sub: string; ctaStudent: string };
  demo: { label: string; student: string; routed: string; category: string; urgency: string; next: string };
  how: { title: string; sub: string; steps: { title: string; body: string }[] };
  offices: { title: string; sub: string; units: { name: string; topics: string }[] };
  sla: { title: string; sub: string; first: string; resolve: string; hourShort: string; pausedNote: string };
  faq: { title: string; items: { q: string; a: string }[] };
  cta: { title: string; body: string; button: string };
  footer: { about: string; rights: string };
}

const en: LandingCopy = {
  nav: { how: "How it works", offices: "Offices", sla: "Response times", faq: "FAQ", signIn: "Sign in", openPortal: "Open portal", skip: "Skip to content" },
  hero: {
    title1: "Student support",
    title2: "at SDU University",
    sub: "Write in Kazakh, Russian or English. Qoldau sends your request to the right department and lets you track the reply.",
    ctaStudent: "Submit a request",
  },
  demo: { label: "Example", student: "A student writes", routed: "Sent to", category: "Topic", urgency: "Urgency", next: "Next example" },
  how: {
    title: "How it works",
    sub: "Every request follows the same transparent path. You always see where it is and who is working on it.",
    steps: [
      { title: "Describe the issue", body: "Explain what happened and what the support team can help you with." },
      { title: "Qoldau checks the topic", body: "The system identifies the likely topic and applies priority rules." },
      { title: "An office gets your request", body: "Clear requests go to the responsible office. The triage team reviews unclear ones." },
      { title: "Track it and talk", body: "Follow every step on a live timeline, chat with your agent, and rate the result when it’s solved." },
    ],
  },
  offices: {
    title: "Who answers your request",
    sub: "Qoldau knows which office handles what. If a request is unclear, Student Services reviews it personally.",
    units: [
      { name: "Dean’s Office", topics: "Grade appeals, retakes, academic leave" },
      { name: "Registrar Office", topics: "Course registration, transcripts, certificates" },
      { name: "Finance Office", topics: "Tuition, scholarships, refunds" },
      { name: "IT Help Desk", topics: "Moodle, email, Wi-Fi, accounts" },
      { name: "Student Housing", topics: "Dormitory places, repairs, roommates" },
      { name: "Main Library", topics: "Books, databases, study rooms" },
      { name: "Medical & Counselling", topics: "Health, psychological support" },
      { name: "International Office", topics: "Visas, exchange, mobility" },
      { name: "Student Services", topics: "Everything else — we’ll find out" },
    ],
  },
  sla: {
    title: "How fast you’ll hear back",
    sub: "Urgency is detected automatically. If a deadline is missed, the head of the office is alerted.",
    first: "First reply",
    resolve: "Resolution",
    hourShort: "hr",
    pausedNote: "The timer pauses while an office is waiting for your reply.",
  },
  faq: {
    title: "Questions students ask",
    items: [
      { q: "Which language should I write in?", a: "Any of Kazakh, Russian or English — even mixed. Qoldau reads all three." },
      { q: "What if my request reaches the wrong office?", a: "The triage team reviews unclear requests and can send them to another office. You can follow the assignment in your request." },
      { q: "Who can see my request?", a: "You, authorised staff handling the request, triage staff when review is needed, and authorised administrators. Staff notes are visible to authorised staff." },
      { q: "What happens when it’s solved?", a: "You get a notification and can rate the service from 1 to 5. If you rate it 2 or lower, the request is reopened and the head of the office reviews it." },
    ],
  },
  cta: { title: "Got a question for the university?", body: "It takes about a minute. You’ll get a request ID right away.", button: "Submit a request" },
  footer: {
    about: "Qoldau is the student support platform of SDU University, Kaskelen, Kazakhstan.",
    rights: "SDU University",
  },
};

const ru: LandingCopy = {
  nav: { how: "Как это работает", offices: "Отделы", sla: "Сроки ответа", faq: "Вопросы", signIn: "Войти", openPortal: "Открыть портал", skip: "Перейти к содержимому" },
  hero: {
    title1: "Поддержка студентов",
    title2: "SDU University",
    sub: "Напишите на казахском, русском или английском. Qoldau направит обращение в нужный отдел, покажет статус и сообщит об ответе.",
    ctaStudent: "Отправить обращение",
  },
  demo: { label: "Пример", student: "Студент пишет", routed: "Направлено в", category: "Тема", urgency: "Срочность", next: "Следующий пример" },
  how: {
    title: "Как это работает",
    sub: "Каждое обращение проходит прозрачный путь. Вы всегда видите, где оно и кто им занимается.",
    steps: [
      { title: "Опишите проблему", body: "Расскажите, что произошло и какая помощь вам нужна." },
      { title: "Qoldau проверяет тему", body: "Система определяет вероятную тему и применяет правила срочности." },
      { title: "Отдел получает обращение", body: "Понятные обращения сразу направляются в отдел. Остальные проверяет дежурная команда." },
      { title: "Следите и общайтесь", body: "Смотрите каждый шаг на живой ленте, переписывайтесь с сотрудником и оцените результат." },
    ],
  },
  offices: {
    title: "Кто отвечает на ваше обращение",
    sub: "Qoldau знает, какой отдел за что отвечает. Если обращение неясное, его лично проверит служба поддержки студентов.",
    units: [
      { name: "Деканат", topics: "Апелляции, пересдачи, академический отпуск" },
      { name: "Офис регистратора", topics: "Регистрация на курсы, транскрипты, справки" },
      { name: "Финансовый отдел", topics: "Оплата обучения, стипендии, возвраты" },
      { name: "IT Help Desk", topics: "Moodle, почта, Wi-Fi, аккаунты" },
      { name: "Отдел общежитий", topics: "Места, ремонт, соседи" },
      { name: "Библиотека", topics: "Книги, базы данных, читальные залы" },
      { name: "Медицинский и психологический центр", topics: "Здоровье, психологическая поддержка" },
      { name: "Международный отдел", topics: "Визы, обмен, мобильность" },
      { name: "Служба поддержки студентов", topics: "Всё остальное — разберёмся" },
    ],
  },
  sla: {
    title: "Как быстро вам ответят",
    sub: "Срочность определяется автоматически. Если срок нарушен, руководитель отдела получает уведомление.",
    first: "Первый ответ",
    resolve: "Решение",
    hourShort: "ч",
    pausedNote: "Таймер останавливается, пока отдел ждёт вашего ответа.",
  },
  faq: {
    title: "Частые вопросы",
    items: [
      { q: "На каком языке писать?", a: "На казахском, русском или английском — можно даже вперемешку. Qoldau понимает все три." },
      { q: "Что делать, если обращение попало в другой отдел?", a: "Дежурная команда проверяет обращения, по которым нужен ручной разбор, и может направить их в другой отдел. Назначенный отдел виден в карточке." },
      { q: "Кто видит моё обращение?", a: "Вы, уполномоченные сотрудники, работающие с обращением, дежурная команда при ручном разборе и администраторы с правом доступа. Служебные заметки доступны уполномоченным сотрудникам." },
      { q: "Что будет после решения?", a: "Вы получите уведомление и сможете оценить работу от 1 до 5. При оценке 2 и ниже обращение переоткроется и его проверит руководитель отдела." },
    ],
  },
  cta: { title: "Есть вопрос к университету?", body: "Это займёт около минуты. Номер обращения вы получите сразу.", button: "Отправить обращение" },
  footer: {
    about: "Qoldau — платформа поддержки студентов SDU University, Каскелен, Казахстан.",
    rights: "SDU University",
  },
};

const kz: LandingCopy = {
  nav: { how: "Қалай жұмыс істейді", offices: "Бөлімдер", sla: "Жауап мерзімі", faq: "Сұрақтар", signIn: "Кіру", openPortal: "Порталды ашу", skip: "Мазмұнға өту" },
  hero: {
    title1: "SDU студенттеріне",
    title2: "қолдау",
    sub: "Қазақ, орыс немесе ағылшын тілінде жазыңыз. Qoldau өтінішті тиісті бөлімге жіберіп, мәртебесін көрсетеді.",
    ctaStudent: "Өтініш жіберу",
  },
  demo: { label: "Мысал", student: "Студент жазады", routed: "Жіберілді", category: "Тақырып", urgency: "Шұғылдық", next: "Келесі мысал" },
  how: {
    title: "Бұл қалай жұмыс істейді",
    sub: "Әр өтініш ашық жолмен өтеді. Оның қайда екенін және кім айналысып жатқанын әрқашан көресіз.",
    steps: [
      { title: "Мәселені сипаттаңыз", body: "Не болғанын және қандай көмек қажет екенін жазыңыз." },
      { title: "Qoldau тақырыпты тексереді", body: "Жүйе ықтимал тақырыпты анықтап, шұғылдық ережелерін қолданады." },
      { title: "Бөлім өтінішті қабылдайды", body: "Түсінікті өтініштер жауапты бөлімге жіберіледі. Қалғанын кезекші топ қарайды." },
      { title: "Бақылаңыз және сөйлесіңіз", body: "Әр қадамды тірі лентадан көріп, қызметкермен хат алмасып, нәтижені бағалаңыз." },
    ],
  },
  offices: {
    title: "Өтінішіңізге кім жауап береді",
    sub: "Qoldau қай бөлім неге жауапты екенін біледі. Өтініш түсініксіз болса, оны студенттерді қолдау қызметі өзі тексереді.",
    units: [
      { name: "Деканат", topics: "Апелляция, қайта тапсыру, академиялық демалыс" },
      { name: "Тіркеу кеңсесі", topics: "Курстарға тіркелу, транскрипт, анықтамалар" },
      { name: "Қаржы бөлімі", topics: "Оқу ақысы, шәкіртақы, қайтару" },
      { name: "IT Help Desk", topics: "Moodle, пошта, Wi-Fi, аккаунттар" },
      { name: "Жатақхана бөлімі", topics: "Орын, жөндеу, бөлмелестер" },
      { name: "Кітапхана", topics: "Кітаптар, дерекқорлар, оқу залдары" },
      { name: "Медициналық-психологиялық орталық", topics: "Денсаулық, психологиялық көмек" },
      { name: "Халықаралық бөлім", topics: "Виза, алмасу, академиялық ұтқырлық" },
      { name: "Студенттерді қолдау қызметі", topics: "Қалғанының бәрі — анықтаймыз" },
    ],
  },
  sla: {
    title: "Қаншалықты тез жауап аласыз",
    sub: "Шұғылдық автоматты түрде анықталады. Мерзім бұзылса, бөлім басшысына хабарлама барады.",
    first: "Алғашқы жауап",
    resolve: "Шешім",
    hourShort: "сағ",
    pausedNote: "Бөлім сіздің жауабыңызды күтіп тұрғанда таймер тоқтайды.",
  },
  faq: {
    title: "Жиі қойылатын сұрақтар",
    items: [
      { q: "Қай тілде жазу керек?", a: "Қазақша, орысша немесе ағылшынша — тіпті аралас та болады. Qoldau үшеуін де түсінеді." },
      { q: "Өтінішім басқа бөлімге түссе ше?", a: "Кезекші топ түсініксіз өтініштерді қарап, оларды басқа бөлімге жібере алады. Жауапты бөлім өтініште көрсетіледі." },
      { q: "Өтінішімді кім көреді?", a: "Өзіңіз, өтінішпен жұмыс істейтін уәкілетті қызметкерлер, тексеру қажет болса кезекші топ және рұқсаты бар әкімшілер. Қызметтік жазбалар уәкілетті қызметкерлерге қолжетімді." },
      { q: "Шешілгеннен кейін не болады?", a: "Хабарлама аласыз және қызметті 1-ден 5-ке дейін бағалай аласыз. 2 және одан төмен бағаласаңыз, өтініш қайта ашылып, бөлім басшысы қарайды." },
    ],
  },
  cta: { title: "Университетке сұрағыңыз бар ма?", body: "Бар болғаны бір минут. Өтініш нөмірін бірден аласыз.", button: "Өтініш жіберу" },
  footer: {
    about: "Qoldau — SDU University студенттерін қолдау платформасы, Қаскелең, Қазақстан.",
    rights: "SDU University",
  },
};

export const LANDING: Record<Lang, LandingCopy> = { en, ru, kz };

/** `office` indexes the translated office names for the illustrative examples. */
export const DEMO_REQUESTS = [
  { lang: "KZ", text: "Жатақхана бөлмесінде жылу жоқ, үш күннен бері суық", category: { en: "Dormitory & Housing", ru: "Общежитие и жильё", kz: "Жатақхана және тұрғын үй" }, office: 4, priority: "Medium" },
  { lang: "EN", text: "I cannot log in to Moodle and my exam starts tomorrow morning", category: { en: "IT Support", ru: "IT-поддержка", kz: "IT қолдау" }, office: 3, priority: "High" },
  { lang: "RU", text: "Нужна справка с места учёбы для визы, когда можно забрать?", category: { en: "Documents & Certificates", ru: "Документы и справки", kz: "Құжаттар мен анықтамалар" }, office: 1, priority: "Medium" },
  { lang: "EN", text: "I feel unsafe in my dorm room and need help", category: { en: "Health & Wellbeing", ru: "Здоровье и благополучие", kz: "Денсаулық және әл-ауқат" }, office: 6, priority: "Critical" },
] as const;
