import type { Lang } from "./types";

/** Landing page copy (KZ/RU/EN). Facts mirror the real configuration: 10 categories, 9 offices, SLA policies. */
export interface LandingCopy {
  nav: { how: string; offices: string; sla: string; faq: string; signIn: string; openPortal: string; skip: string };
  hero: { title1: string; title2: string; sub: string; ctaStudent: string; ctaStaff: string; note: string };
  demo: { label: string; student: string; routed: string; category: string; urgency: string; firstResponse: string; next: string };
  how: { title: string; sub: string; steps: { title: string; body: string }[] };
  offices: { title: string; sub: string; units: { name: string; topics: string }[] };
  sla: { title: string; sub: string; priority: string; first: string; resolve: string; when: string; rows: { p: string; first: string; resolve: string; when: string }[]; pausedNote: string };
  faq: { title: string; items: { q: string; a: string }[] };
  cta: { title: string; body: string; button: string };
  footer: { about: string; rights: string; privacy: string };
}

const en: LandingCopy = {
  nav: { how: "How it works", offices: "Offices", sla: "Response times", faq: "FAQ", signIn: "Sign in", openPortal: "Open portal", skip: "Skip to content" },
  hero: {
    title1: "Ask once.",
    title2: "We’ll find the right office.",
    sub: "Write your question in Kazakh, Russian or English. Qoldau sends it to the office that can solve it and keeps you updated until it’s done.",
    ctaStudent: "Submit a request",
    ctaStaff: "Staff sign in",
    note: "Sign in with your SDU account. No forms to figure out, no office to guess.",
  },
  demo: { label: "Example", student: "A student writes", routed: "Sent to", category: "Topic", urgency: "Urgency", firstResponse: "First reply within", next: "Next example" },
  how: {
    title: "How it works",
    sub: "Every request follows the same transparent path. You always see where it is and who is working on it.",
    steps: [
      { title: "Write it in your words", body: "Describe the problem and attach a screenshot or document if you have one. No need to pick the right office." },
      { title: "AI understands it", body: "Qoldau detects the topic and urgency. Health and safety issues are flagged as critical within a second." },
      { title: "The right office takes it", body: "Your request goes straight to the responsible office and the agent with the lightest queue." },
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
    priority: "Urgency",
    first: "First reply",
    resolve: "Resolution",
    when: "Typical case",
    rows: [
      { p: "Critical", first: "1 hour", resolve: "8 hours", when: "Health, safety, harassment" },
      { p: "High", first: "4 hours", resolve: "24 hours", when: "Deadline within 48 h, exam, blocked payment" },
      { p: "Medium", first: "24 hours", resolve: "3 days", when: "Regular service request" },
      { p: "Low", first: "48 hours", resolve: "5 days", when: "Information question, feedback" },
    ],
    pausedNote: "The timer pauses while an office is waiting for your reply.",
  },
  faq: {
    title: "Questions students ask",
    items: [
      { q: "Which language should I write in?", a: "Any of Kazakh, Russian or English — even mixed. Qoldau reads all three." },
      { q: "What if the AI picks the wrong office?", a: "If it isn’t confident, a person from Student Services checks your request first. Agents can also re-route it in one click — and every correction makes the system smarter." },
      { q: "Who can see my request?", a: "Only you and the staff of the office handling it. Staff notes about your case are internal, and files are shared through private, expiring links." },
      { q: "Can I attach documents?", a: "Yes — PDF, JPG, PNG and DOCX up to 10 MB each, both when you submit and later in the chat." },
      { q: "What happens when it’s solved?", a: "You get a notification and can rate the service from 1 to 5. If you rate it 2 or lower, the request is reopened and the head of the office reviews it." },
    ],
  },
  cta: { title: "Got a question for the university?", body: "It takes about a minute. You’ll get a request ID right away.", button: "Submit a request" },
  footer: {
    about: "Qoldau is the student support platform of SDU University, Kaskelen, Kazakhstan.",
    rights: "SDU University",
    privacy: "Your requests are visible only to you and the responsible office.",
  },
};

const ru: LandingCopy = {
  nav: { how: "Как это работает", offices: "Отделы", sla: "Сроки ответа", faq: "Вопросы", signIn: "Войти", openPortal: "Открыть портал", skip: "Перейти к содержимому" },
  hero: {
    title1: "Спросите один раз.",
    title2: "Мы найдём нужный отдел.",
    sub: "Напишите вопрос на казахском, русском или английском. Qoldau отправит его в отдел, который может помочь, и будет сообщать вам о каждом шаге.",
    ctaStudent: "Отправить обращение",
    ctaStaff: "Вход для сотрудников",
    note: "Вход через аккаунт SDU. Не нужно разбираться в формах и угадывать отдел.",
  },
  demo: { label: "Пример", student: "Студент пишет", routed: "Направлено в", category: "Тема", urgency: "Срочность", firstResponse: "Первый ответ в течение", next: "Следующий пример" },
  how: {
    title: "Как это работает",
    sub: "Каждое обращение проходит прозрачный путь. Вы всегда видите, где оно и кто им занимается.",
    steps: [
      { title: "Напишите своими словами", body: "Опишите проблему и при необходимости приложите скриншот или документ. Выбирать отдел не нужно." },
      { title: "ИИ понимает суть", body: "Qoldau определяет тему и срочность. Вопросы здоровья и безопасности помечаются как критические за секунду." },
      { title: "Нужный отдел берёт в работу", body: "Обращение сразу попадает в ответственный отдел — к сотруднику с наименьшей загрузкой." },
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
    priority: "Срочность",
    first: "Первый ответ",
    resolve: "Решение",
    when: "Типичный случай",
    rows: [
      { p: "Critical", first: "1 час", resolve: "8 часов", when: "Здоровье, безопасность, домогательства" },
      { p: "High", first: "4 часа", resolve: "24 часа", when: "Дедлайн в течение 48 ч, экзамен, блокировка оплаты" },
      { p: "Medium", first: "24 часа", resolve: "3 дня", when: "Обычный запрос" },
      { p: "Low", first: "48 часов", resolve: "5 дней", when: "Информационный вопрос, отзыв" },
    ],
    pausedNote: "Таймер останавливается, пока отдел ждёт вашего ответа.",
  },
  faq: {
    title: "Частые вопросы",
    items: [
      { q: "На каком языке писать?", a: "На казахском, русском или английском — можно даже вперемешку. Qoldau понимает все три." },
      { q: "А если ИИ выберет не тот отдел?", a: "Если система не уверена, обращение сначала проверит сотрудник службы поддержки. Сотрудники также могут перенаправить его в один клик — и каждая правка делает систему точнее." },
      { q: "Кто видит моё обращение?", a: "Только вы и сотрудники ответственного отдела. Служебные заметки внутренние, а файлы передаются по закрытым временным ссылкам." },
      { q: "Можно приложить документы?", a: "Да — PDF, JPG, PNG и DOCX до 10 МБ, и при отправке, и позже в чате." },
      { q: "Что будет после решения?", a: "Вы получите уведомление и сможете оценить работу от 1 до 5. При оценке 2 и ниже обращение переоткроется и его проверит руководитель отдела." },
    ],
  },
  cta: { title: "Есть вопрос к университету?", body: "Это займёт около минуты. Номер обращения вы получите сразу.", button: "Отправить обращение" },
  footer: {
    about: "Qoldau — платформа поддержки студентов SDU University, Каскелен, Казахстан.",
    rights: "SDU University",
    privacy: "Ваши обращения видите только вы и ответственный отдел.",
  },
};

const kz: LandingCopy = {
  nav: { how: "Қалай жұмыс істейді", offices: "Бөлімдер", sla: "Жауап мерзімі", faq: "Сұрақтар", signIn: "Кіру", openPortal: "Порталды ашу", skip: "Мазмұнға өту" },
  hero: {
    title1: "Бір рет сұраңыз.",
    title2: "Қажетті бөлімді біз табамыз.",
    sub: "Сұрағыңызды қазақ, орыс немесе ағылшын тілінде жазыңыз. Qoldau оны көмектесе алатын бөлімге жібереді және әр қадамды хабарлап отырады.",
    ctaStudent: "Өтініш жіберу",
    ctaStaff: "Қызметкерлерге кіру",
    note: "SDU аккаунтымен кіріңіз. Күрделі формалар да, бөлімді болжау да қажет емес.",
  },
  demo: { label: "Мысал", student: "Студент жазады", routed: "Жіберілді", category: "Тақырып", urgency: "Шұғылдық", firstResponse: "Алғашқы жауап", next: "Келесі мысал" },
  how: {
    title: "Бұл қалай жұмыс істейді",
    sub: "Әр өтініш ашық жолмен өтеді. Оның қайда екенін және кім айналысып жатқанын әрқашан көресіз.",
    steps: [
      { title: "Өз сөзіңізбен жазыңыз", body: "Мәселені сипаттап, қажет болса скриншот немесе құжат тіркеңіз. Бөлімді таңдаудың қажеті жоқ." },
      { title: "ЖИ мәнін түсінеді", body: "Qoldau тақырып пен шұғылдықты анықтайды. Денсаулық пен қауіпсіздік мәселелері бір секундта шұғыл деп белгіленеді." },
      { title: "Қажетті бөлім қолға алады", body: "Өтініш бірден жауапты бөлімге — жүктемесі ең аз қызметкерге түседі." },
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
    priority: "Шұғылдық",
    first: "Алғашқы жауап",
    resolve: "Шешім",
    when: "Әдеттегі жағдай",
    rows: [
      { p: "Critical", first: "1 сағат", resolve: "8 сағат", when: "Денсаулық, қауіпсіздік, қудалау" },
      { p: "High", first: "4 сағат", resolve: "24 сағат", when: "48 сағат ішіндегі дедлайн, емтихан, төлем бұғатталуы" },
      { p: "Medium", first: "24 сағат", resolve: "3 күн", when: "Қарапайым сұраныс" },
      { p: "Low", first: "48 сағат", resolve: "5 күн", when: "Ақпараттық сұрақ, пікір" },
    ],
    pausedNote: "Бөлім сіздің жауабыңызды күтіп тұрғанда таймер тоқтайды.",
  },
  faq: {
    title: "Жиі қойылатын сұрақтар",
    items: [
      { q: "Қай тілде жазу керек?", a: "Қазақша, орысша немесе ағылшынша — тіпті аралас та болады. Qoldau үшеуін де түсінеді." },
      { q: "ЖИ басқа бөлімді таңдап қойса ше?", a: "Жүйе сенімсіз болса, өтінішті алдымен қолдау қызметінің маманы тексереді. Қызметкерлер оны бір басумен қайта бағыттай алады — әр түзету жүйені дәлірек етеді." },
      { q: "Өтінішімді кім көреді?", a: "Тек сіз және жауапты бөлімнің қызметкерлері. Қызметтік жазбалар ішкі, ал файлдар жабық уақытша сілтемелер арқылы беріледі." },
      { q: "Құжат тіркеуге бола ма?", a: "Иә — PDF, JPG, PNG және DOCX, әрқайсысы 10 МБ-қа дейін, жіберу кезінде де, кейін чатта да." },
      { q: "Шешілгеннен кейін не болады?", a: "Хабарлама аласыз және қызметті 1-ден 5-ке дейін бағалай аласыз. 2 және одан төмен бағаласаңыз, өтініш қайта ашылып, бөлім басшысы қарайды." },
    ],
  },
  cta: { title: "Университетке сұрағыңыз бар ма?", body: "Бар болғаны бір минут. Өтініш нөмірін бірден аласыз.", button: "Өтініш жіберу" },
  footer: {
    about: "Qoldau — SDU University студенттерін қолдау платформасы, Қаскелең, Қазақстан.",
    rights: "SDU University",
    privacy: "Өтініштеріңізді тек сіз және жауапты бөлім көреді.",
  },
};

export const LANDING: Record<Lang, LandingCopy> = { en, ru, kz };

/** Real examples the hero demo cycles through (classified by the actual model during development). */
/**
 * Real examples the hero demo cycles through. Category, urgency and confidence are the actual model output
 * (checked against backend/app/ml at the time of writing); `office` indexes LandingCopy.offices.units.
 */
export const DEMO_REQUESTS = [
  { lang: "KZ", text: "Жатақхана бөлмесінде жылу жоқ, үш күннен бері суық", category: { en: "Dormitory & Housing", ru: "Общежитие и жильё", kz: "Жатақхана және тұрғын үй" }, office: 4, priority: "Medium", first: { en: "24 h", ru: "24 ч", kz: "24 сағ" }, confidence: 99 },
  { lang: "EN", text: "I cannot log in to Moodle and my exam starts tomorrow morning", category: { en: "IT Support", ru: "IT-поддержка", kz: "IT қолдау" }, office: 3, priority: "High", first: { en: "4 h", ru: "4 ч", kz: "4 сағ" }, confidence: 66 },
  { lang: "RU", text: "Нужна справка с места учёбы для визы, когда можно забрать?", category: { en: "Documents & Certificates", ru: "Документы и справки", kz: "Құжаттар мен анықтамалар" }, office: 1, priority: "Medium", first: { en: "24 h", ru: "24 ч", kz: "24 сағ" }, confidence: 98 },
  { lang: "EN", text: "I feel unsafe in my dorm room and need help", category: { en: "Health & Wellbeing", ru: "Здоровье и благополучие", kz: "Денсаулық және әл-ауқат" }, office: 6, priority: "Critical", first: { en: "1 h", ru: "1 ч", kz: "1 сағ" }, confidence: 98 },
] as const;
