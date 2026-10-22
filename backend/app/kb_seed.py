"""Knowledge-base seed content (US21): 20 FAQ topics (2 per category) in KZ / RU / EN, 15 reply
templates and per-category agent replies used by the demo request generator."""

# slug -> (category, {lang: (title, body_html, tags)})
FAQ: dict[str, tuple[str, dict[str, tuple[str, str, list[str]]]]] = {
    "grade-appeal": ("Academic", {
        "en": ("How to appeal a grade",
               "<p>You can appeal an exam or course grade within <strong>3 working days</strong> after it is published.</p>"
               "<ul><li>Submit a request in Qoldau (category Academic) with the course code and the assessment.</li>"
               "<li>Explain which answers you think were marked incorrectly.</li></ul>"
               "<p>The Dean's Office forms an appeal commission; the decision is final.</p>", ["grade", "appeal", "exam"]),
        "ru": ("Как подать апелляцию на оценку",
               "<p>Апелляцию на оценку за экзамен или курс можно подать в течение <strong>3 рабочих дней</strong> после публикации.</p>"
               "<ul><li>Создайте обращение в Qoldau (категория Academic) с кодом курса и видом контроля.</li>"
               "<li>Укажите, какие ответы, по-вашему, оценены неверно.</li></ul>"
               "<p>Деканат собирает апелляционную комиссию; её решение окончательное.</p>", ["оценка", "апелляция", "экзамен"]),
        "kz": ("Бағаға апелляция беру",
               "<p>Емтихан немесе курс бағасына жарияланғаннан кейін <strong>3 жұмыс күні</strong> ішінде апелляция беруге болады.</p>"
               "<ul><li>Qoldau жүйесінде курс коды мен бақылау түрін көрсетіп өтініш жіберіңіз (Academic санаты).</li>"
               "<li>Қай жауаптар қате бағаланды деп ойлайтыныңызды жазыңыз.</li></ul>"
               "<p>Деканат апелляциялық комиссия құрады; оның шешімі түпкілікті.</p>", ["баға", "апелляция", "емтихан"]),
    }),
    "retake-course": ("Academic", {
        "en": ("Retaking a failed course",
               "<p>A failed course is retaken in the summer semester or the next time it is offered. Register for it during "
               "the registration period and pay for the credits at the Finance Office.</p>", ["retake", "failed", "course"]),
        "ru": ("Пересдача заваленного предмета",
               "<p>Заваленный предмет пересдаётся в летнем семестре или когда курс снова открыт. Зарегистрируйтесь на него в период "
               "регистрации и оплатите кредиты в Finance Office.</p>", ["пересдача", "предмет", "курс"]),
        "kz": ("Құлаған пәнді қайта тапсыру",
               "<p>Құлаған пән жазғы семестрде немесе курс қайта ашылғанда қайта оқылады. Тіркелу кезеңінде пәнге тіркеліп, "
               "кредит ақысын Finance Office-ке төлеңіз.</p>", ["қайта тапсыру", "пән", "курс"]),
    }),
    "add-drop-elective": ("Registration & Enrollment", {
        "en": ("Adding or dropping an elective",
               "<p>Electives can be added or dropped during the <strong>add/drop week</strong> in the registration portal. "
               "If the section is full or registration is closed, send a request and the Registrar will check free seats.</p>",
               ["elective", "add drop", "registration"]),
        "ru": ("Добавить или убрать элективный курс",
               "<p>Элективы добавляются и удаляются в <strong>неделю add/drop</strong> в портале регистрации. Если секция "
               "заполнена или регистрация закрыта, отправьте обращение — Registrar проверит свободные места.</p>",
               ["электив", "регистрация", "add drop"]),
        "kz": ("Элективті қосу немесе алып тастау",
               "<p>Элективтер тіркеу порталында <strong>add/drop аптасында</strong> қосылады немесе алынады. Секция толы "
               "немесе тіркелу жабық болса, өтініш жіберіңіз — Registrar бос орындарды тексереді.</p>",
               ["электив", "тіркелу", "add drop"]),
    }),
    "registration-error": ("Registration & Enrollment", {
        "en": ("The registration system shows an error",
               "<p>Clear the browser cache and try again in a private window. Prerequisite and hold errors mean the course "
               "needs a prerequisite or you have an unpaid balance. Send a screenshot of the error in your request.</p>",
               ["registration", "error", "prerequisite"]),
        "ru": ("Система регистрации выдаёт ошибку",
               "<p>Очистите кэш браузера и попробуйте в режиме инкогнито. Ошибки пререквизита или блокировки означают, что "
               "нужен пререквизит или есть задолженность по оплате. Приложите скриншот ошибки к обращению.</p>",
               ["регистрация", "ошибка", "пререквизит"]),
        "kz": ("Тіркеу жүйесі қате көрсетеді",
               "<p>Браузер кэшін тазалап, жасырын терезеде қайталап көріңіз. Пререквизит немесе бұғаттау қатесі пәнге "
               "пререквизит керек немесе төлем қарызы бар екенін білдіреді. Өтінішке қатенің скриншотын тіркеңіз.</p>",
               ["тіркелу", "қате", "пререквизит"]),
    }),
    "scholarship-payment-delay": ("Finance & Scholarships", {
        "en": ("My scholarship payment is late",
               "<p>Scholarships are paid by the <strong>25th</strong> of each month. Delays usually come from a changed "
               "bank card or an academic hold. Check your bank details in the student portal and send a request if the "
               "payment has not arrived by the 28th.</p>", ["scholarship", "stipend", "payment"]),
        "ru": ("Задерживается стипендия",
               "<p>Стипендия выплачивается до <strong>25 числа</strong> каждого месяца. Задержки обычно связаны со сменой "
               "банковской карты или академической задолженностью. Проверьте реквизиты в портале и напишите обращение, "
               "если выплата не пришла до 28 числа.</p>", ["стипендия", "выплата", "задержка"]),
        "kz": ("Шәкіртақы кешігіп жатыр",
               "<p>Шәкіртақы әр айдың <strong>25-іне</strong> дейін төленеді. Кешігу көбіне банк картасының ауысуынан немесе "
               "академиялық қарыздан болады. Порталдағы деректемелерді тексеріп, 28-іне дейін түспесе өтініш жіберіңіз.</p>",
               ["шәкіртақы", "төлем", "кешігу"]),
    }),
    "tuition-payment": ("Finance & Scholarships", {
        "en": ("How to pay tuition",
               "<p>Pay tuition by bank transfer or Kaspi using your student ID as the payment reference. Instalment plans "
               "are approved by the Finance Office; ask before the semester deadline.</p>", ["tuition", "payment", "instalment"]),
        "ru": ("Как оплатить обучение",
               "<p>Оплатить обучение можно банковским переводом или через Kaspi, указав студенческий ID в назначении "
               "платежа. Рассрочку утверждает Finance Office — подайте заявку до дедлайна семестра.</p>",
               ["оплата", "обучение", "рассрочка"]),
        "kz": ("Оқу ақысын қалай төлеуге болады",
               "<p>Оқу ақысын банк аударымы немесе Kaspi арқылы, төлем мақсатында студенттік ID-ді көрсетіп төлеңіз. "
               "Бөліп төлеуді Finance Office бекітеді — семестр мерзіміне дейін өтініш беріңіз.</p>",
               ["оқу ақысы", "төлем", "бөліп төлеу"]),
    }),
    "moodle-password-reset": ("IT Support", {
        "en": ("Resetting your Moodle password",
               "<p>Open <strong>Forgot password</strong> on the Moodle login page and enter your university e-mail. "
               "If the reset e-mail does not arrive within 10 minutes, the IT Help Desk can reset it for you.</p>",
               ["moodle", "password", "login"]),
        "ru": ("Как сбросить пароль Moodle",
               "<p>Нажмите <strong>«Забыли пароль»</strong> на странице входа в Moodle и введите университетскую почту. "
               "Если письмо не пришло за 10 минут, IT Help Desk сбросит пароль за вас.</p>",
               ["moodle", "пароль", "войти", "вход"]),
        "kz": ("Moodle құпиясөзін қалпына келтіру",
               "<p>Moodle кіру бетінде <strong>«Құпиясөзді ұмыттыңыз ба»</strong> батырмасын басып, университет поштасын "
               "енгізіңіз. Хат 10 минутта келмесе, IT Help Desk құпиясөзді өзі қалпына келтіреді.</p>",
               ["moodle", "құпиясөз", "кіру"]),
    }),
    "campus-wifi": ("IT Support", {
        "en": ("Connecting to campus Wi-Fi",
               "<p>Connect to <strong>SDU-Students</strong> with your university e-mail and password. On phones choose "
               "PEAP / MSCHAPv2 and do not validate the certificate.</p>", ["wifi", "internet", "eduroam"]),
        "ru": ("Подключение к Wi-Fi в кампусе",
               "<p>Подключитесь к сети <strong>SDU-Students</strong> с университетской почтой и паролем. На телефоне выберите "
               "PEAP / MSCHAPv2 и не проверяйте сертификат.</p>", ["wifi", "интернет", "сеть"]),
        "kz": ("Кампустағы Wi-Fi-ға қосылу",
               "<p><strong>SDU-Students</strong> желісіне университет поштасы мен құпиясөз арқылы қосылыңыз. Телефонда "
               "PEAP / MSCHAPv2 таңдап, сертификатты тексермеңіз.</p>", ["wifi", "интернет", "желі"]),
    }),
    "dorm-repair": ("Dormitory & Housing", {
        "en": ("Reporting a repair in your dorm room",
               "<p>Send a request with your dorm and room number and a photo of the problem. Urgent leaks or electrical "
               "issues are fixed the same day; other repairs within 3 working days.</p>", ["dorm", "repair", "room"]),
        "ru": ("Ремонт в комнате общежития",
               "<p>Отправьте обращение с номером общежития и комнаты и фото проблемы. Срочные протечки и электрика "
               "устраняются в тот же день, остальной ремонт — за 3 рабочих дня.</p>", ["общежитие", "ремонт", "комната"]),
        "kz": ("Жатақхана бөлмесіндегі жөндеу",
               "<p>Жатақхана мен бөлме нөмірін және мәселенің фотосын көрсетіп өтініш жіберіңіз. Шұғыл ағу мен электр "
               "ақаулары сол күні, қалған жөндеу 3 жұмыс күнінде жасалады.</p>", ["жатақхана", "жөндеу", "бөлме"]),
    }),
    "dorm-room-change": ("Dormitory & Housing", {
        "en": ("Changing rooms or a roommate conflict",
               "<p>Room changes are possible when a place is free. Describe the reason in a request; for conflicts the "
               "Student Housing Office first offers a mediated conversation.</p>", ["dorm", "roommate", "room change"]),
        "ru": ("Смена комнаты или конфликт с соседом",
               "<p>Сменить комнату можно при наличии свободного места. Опишите причину в обращении; при конфликте "
               "Student Housing Office сначала предлагает разговор с медиатором.</p>", ["общежитие", "сосед", "комната"]),
        "kz": ("Бөлмені ауыстыру немесе көршімен келіспеушілік",
               "<p>Бос орын болса, бөлмені ауыстыруға болады. Себебін өтінішке жазыңыз; келіспеушілік кезінде Student "
               "Housing Office алдымен медиатормен сөйлесуді ұсынады.</p>", ["жатақхана", "көрші", "бөлме"]),
    }),
    "ordering-transcript": ("Documents & Certificates", {
        "en": ("Ordering a transcript",
               "<p>Order an official transcript of records with a Qoldau request (category Documents &amp; Certificates). "
               "It is ready in <strong>2 working days</strong>; collect it at the Registrar Office with your student ID. "
               "Translated or apostilled copies take 5 working days.</p>", ["transcript", "documents", "registrar"]),
        "ru": ("Как заказать транскрипт",
               "<p>Закажите официальный транскрипт через обращение в Qoldau (категория Documents &amp; Certificates). "
               "Он готов через <strong>2 рабочих дня</strong>; заберите его в Registrar Office со студенческим билетом. "
               "Перевод или апостиль — 5 рабочих дней.</p>", ["транскрипт", "документы", "registrar"]),
        "kz": ("Транскриптке тапсырыс беру",
               "<p>Ресми транскриптке Qoldau өтініші арқылы тапсырыс беріңіз (Documents &amp; Certificates санаты). "
               "Ол <strong>2 жұмыс күнінде</strong> дайын болады; студенттік билетпен Registrar Office-тен алыңыз. "
               "Аударма немесе апостиль — 5 жұмыс күні.</p>", ["транскрипт", "құжаттар", "registrar"]),
    }),
    "enrollment-certificate": ("Documents & Certificates", {
        "en": ("Enrollment certificate",
               "<p>An enrollment certificate confirms that you study at SDU (for the embassy, military office, bank or "
               "employer). Request it in Qoldau; the electronic version arrives within 1 working day, the stamped paper "
               "version is collected at the Registrar Office.</p>", ["certificate", "enrollment", "proof of study"]),
        "ru": ("Справка с места учёбы",
               "<p>Справка с места учёбы подтверждает, что вы учитесь в SDU (для посольства, военкомата, банка или "
               "работодателя). Получить справку можно через обращение в Qoldau: электронная версия приходит за 1 рабочий "
               "день, бумажную с печатью забирают в Registrar Office.</p>", ["справка", "место учебы", "документы"]),
        "kz": ("Оқу орнынан анықтама",
               "<p>Оқу орнынан анықтама SDU-да оқитыныңызды растайды (елшілікке, әскери комиссариатқа, банкке немесе "
               "жұмыс берушіге). Анықтаманы Qoldau өтініші арқылы алуға болады: электронды нұсқасы 1 жұмыс күнінде келеді, "
               "мөрі бар қағаз нұсқасын Registrar Office-тен аласыз.</p>", ["анықтама", "оқу орны", "құжаттар"]),
    }),
    "library-book-return": ("Library", {
        "en": ("Returning or renewing library books",
               "<p>Books can be renewed twice online if nobody has reserved them. Late returns cost 100 KZT per day; "
               "return books at the Main Library Desk or the drop box at the entrance.</p>", ["library", "book", "renew"]),
        "ru": ("Возврат и продление книг",
               "<p>Книги можно продлить онлайн дважды, если их никто не забронировал. Просрочка — 100 тенге в день; "
               "вернуть книги можно на Main Library Desk или в ящик у входа.</p>", ["библиотека", "книга", "продление"]),
        "kz": ("Кітапты қайтару немесе ұзарту",
               "<p>Кітапты ешкім брондамаса, онлайн екі рет ұзартуға болады. Кешіктіру күніне 100 теңге; кітапты Main "
               "Library Desk-ке немесе кіреберістегі жәшікке қайтарыңыз.</p>", ["кітапхана", "кітап", "ұзарту"]),
    }),
    "library-database-access": ("Library", {
        "en": ("Access to electronic databases",
               "<p>Scopus, Web of Science and JSTOR are available on campus automatically and from home through the "
               "library proxy with your university login.</p>", ["library", "database", "scopus"]),
        "ru": ("Доступ к электронным базам",
               "<p>Scopus, Web of Science и JSTOR доступны в кампусе автоматически, а из дома — через прокси библиотеки "
               "с университетским логином.</p>", ["библиотека", "база данных", "scopus"]),
        "kz": ("Электронды дерекқорларға қолжетімділік",
               "<p>Scopus, Web of Science және JSTOR кампуста автоматты түрде, ал үйден университет логинімен кітапхана "
               "проксиі арқылы қолжетімді.</p>", ["кітапхана", "дерекқор", "scopus"]),
    }),
    "medical-appointment": ("Health & Wellbeing", {
        "en": ("Seeing a doctor on campus",
               "<p>The Medical Center (building B, ground floor) is open 24/7 for emergencies and 9:00-18:00 for "
               "appointments. In an emergency call 103 first.</p>", ["doctor", "medical", "health"]),
        "ru": ("Приём у врача в кампусе",
               "<p>Медицинский центр (корпус B, первый этаж) работает круглосуточно для экстренных случаев и с 9:00 до "
               "18:00 по записи. В экстренной ситуации сначала звоните 103.</p>", ["врач", "медицина", "здоровье"]),
        "kz": ("Кампуста дәрігерге қаралу",
               "<p>Медициналық орталық (B корпусы, бірінші қабат) шұғыл жағдайда тәулік бойы, жазылу бойынша 9:00-18:00 "
               "жұмыс істейді. Шұғыл жағдайда алдымен 103-ке қоңырау шалыңыз.</p>", ["дәрігер", "медицина", "денсаулық"]),
    }),
    "counselling-support": ("Health & Wellbeing", {
        "en": ("Psychological support",
               "<p>Free and confidential sessions with a university psychologist are available every weekday. "
               "Book through a request or walk in; if you feel unsafe right now, call 150 or 112.</p>",
               ["psychologist", "stress", "counselling"]),
        "ru": ("Психологическая поддержка",
               "<p>Бесплатные и конфиденциальные встречи с психологом университета проходят каждый будний день. "
               "Запишитесь через обращение или приходите без записи; если вы в опасности прямо сейчас, звоните 150 или 112.</p>",
               ["психолог", "стресс", "поддержка"]),
        "kz": ("Психологиялық қолдау",
               "<p>Университет психологымен тегін әрі құпия кездесулер әр жұмыс күні өтеді. Өтініш арқылы жазылыңыз "
               "немесе жазылусыз келіңіз; қазір қауіп төнсе, 150 немесе 112-ге қоңырау шалыңыз.</p>",
               ["психолог", "стресс", "қолдау"]),
    }),
    "visa-support-letter": ("International Office", {
        "en": ("Visa support letter",
               "<p>International students get a visa support letter and registration help from the International Office. "
               "Send your passport copy and travel dates at least <strong>30 days</strong> before your visa expires.</p>",
               ["visa", "invitation", "international"]),
        "ru": ("Визовая поддержка",
               "<p>Иностранные студенты получают письмо визовой поддержки и помощь с регистрацией в International Office. "
               "Отправьте копию паспорта и даты поездки минимум за <strong>30 дней</strong> до окончания визы.</p>",
               ["виза", "приглашение", "международный"]),
        "kz": ("Визалық қолдау",
               "<p>Шетелдік студенттер International Office-тен визалық қолдау хатын және тіркеуге көмек алады. Паспорт "
               "көшірмесі мен сапар күндерін виза біткенге дейін кемінде <strong>30 күн</strong> бұрын жіберіңіз.</p>",
               ["виза", "шақыру", "халықаралық"]),
    }),
    "exchange-program": ("International Office", {
        "en": ("Applying for an exchange semester",
               "<p>Exchange applications open in October (spring semester) and March (fall semester). You need a GPA of "
               "at least 3.0 and an English certificate.</p>", ["exchange", "erasmus", "study abroad"]),
        "ru": ("Как поехать по обмену",
               "<p>Приём заявок на обмен открывается в октябре (весенний семестр) и в марте (осенний семестр). Нужен GPA "
               "не ниже 3.0 и сертификат по английскому.</p>", ["обмен", "erasmus", "учёба за рубежом"]),
        "kz": ("Алмасу бағдарламасына өтініш беру",
               "<p>Алмасуға өтініштер қазанда (көктемгі семестр) және наурызда (күзгі семестр) қабылданады. GPA кемінде "
               "3.0 және ағылшын тілі сертификаты қажет.</p>", ["алмасу", "erasmus", "шетелде оқу"]),
    }),
    "contact-student-services": ("Other", {
        "en": ("Not sure where to ask?",
               "<p>Just describe your question in a Qoldau request and choose “Not sure”. Student Services reads every "
               "unclear request and forwards it to the right office, usually within one working day.</p>",
               ["help", "question", "student services"]),
        "ru": ("Не знаете, куда обратиться?",
               "<p>Просто опишите вопрос в обращении Qoldau и выберите «Не уверен». Student Services читает каждое "
               "неясное обращение и передаёт его в нужный отдел, обычно в течение рабочего дня.</p>",
               ["помощь", "вопрос", "student services"]),
        "kz": ("Қайда жүгінерді білмейсіз бе?",
               "<p>Сұрағыңызды Qoldau өтінішінде сипаттап, «Сенімді емеспін» таңдаңыз. Student Services әр түсініксіз "
               "өтінішті оқып, оны тиісті бөлімге, әдетте бір жұмыс күні ішінде жібереді.</p>",
               ["көмек", "сұрақ", "student services"]),
    }),
    "student-id-card": ("Other", {
        "en": ("Lost student ID card",
               "<p>Block your card at the security desk, then request a new one. A replacement costs 2,000 KZT and is "
               "ready in 3 working days.</p>", ["student id", "card", "lost"]),
        "ru": ("Потерян студенческий билет",
               "<p>Заблокируйте карту на посту охраны, затем подайте заявку на новую. Замена стоит 2 000 тенге и готова "
               "через 3 рабочих дня.</p>", ["студенческий", "карта", "потерян"]),
        "kz": ("Студенттік билет жоғалды",
               "<p>Картаны күзет бекетінде бұғаттаңыз, содан кейін жаңасына өтініш беріңіз. Ауыстыру 2 000 теңге тұрады "
               "және 3 жұмыс күнінде дайын болады.</p>", ["студенттік", "карта", "жоғалды"]),
    }),
}

# (category, language, title, body)
TEMPLATES: list[tuple[str, str, str, str]] = [
    ("IT Support", "en", "Moodle password reset",
     "Hello {student_name},\n\nI have reset your Moodle password. Please use \"Forgot password\" on the login page and "
     "follow the link sent to your university e-mail; it is valid for 1 hour. Let me know if you still cannot log in.\n\n"
     "{agent_name}, {unit}"),
    ("IT Support", "ru", "Сброс пароля Moodle",
     "Здравствуйте, {student_name}!\n\nЯ сбросил(а) ваш пароль в Moodle. Нажмите «Забыли пароль» на странице входа и "
     "перейдите по ссылке из письма на университетскую почту — она действует 1 час. Если войти всё ещё не получается, "
     "напишите мне.\n\n{agent_name}, {unit}"),
    ("IT Support", "kz", "Moodle құпиясөзін қалпына келтіру",
     "Сәлеметсіз бе, {student_name}!\n\nMoodle құпиясөзіңізді қалпына келтірдім. Кіру бетінде «Құпиясөзді ұмыттыңыз ба» "
     "батырмасын басып, университет поштасына келген сілтемеге өтіңіз — ол 1 сағат жарамды. Әлі кіре алмасаңыз, "
     "жазыңыз.\n\n{agent_name}, {unit}"),
    ("Documents & Certificates", "en", "Document ready for pickup",
     "Hello {student_name},\n\nYour document for request {request_id} is ready. Please collect it at the Registrar Office "
     "(room 105, 9:00-17:00) with your student ID.\n\n{agent_name}, {unit}"),
    ("Documents & Certificates", "ru", "Документ готов к выдаче",
     "Здравствуйте, {student_name}!\n\nДокумент по обращению {request_id} готов. Заберите его в Registrar Office "
     "(кабинет 105, 9:00-17:00) со студенческим билетом.\n\n{agent_name}, {unit}"),
    ("Documents & Certificates", "kz", "Құжат дайын",
     "Сәлеметсіз бе, {student_name}!\n\n{request_id} өтініші бойынша құжатыңыз дайын. Оны студенттік билетпен Registrar "
     "Office-тен (105 кабинет, 9:00-17:00) алыңыз.\n\n{agent_name}, {unit}"),
    ("Finance & Scholarships", "en", "Scholarship payment check",
     "Hello {student_name},\n\nWe checked your scholarship: the payment was sent to the bank card in your profile. If the "
     "card was changed recently, please update your bank details in the student portal and we will resend it within 3 "
     "working days.\n\n{agent_name}, {unit}"),
    ("Finance & Scholarships", "ru", "Проверка выплаты стипендии",
     "Здравствуйте, {student_name}!\n\nМы проверили выплату: стипендия отправлена на карту из вашего профиля. Если вы "
     "недавно меняли карту, обновите реквизиты в портале — мы отправим выплату повторно в течение 3 рабочих дней.\n\n"
     "{agent_name}, {unit}"),
    ("Dormitory & Housing", "en", "Repair request registered",
     "Hello {student_name},\n\nYour repair request is registered and a technician will visit your room within 3 working "
     "days (urgent issues today). Please make sure someone can open the door.\n\n{agent_name}, {unit}"),
    ("Dormitory & Housing", "ru", "Заявка на ремонт принята",
     "Здравствуйте, {student_name}!\n\nЗаявка на ремонт принята, мастер придёт в течение 3 рабочих дней (срочные "
     "проблемы — сегодня). Пожалуйста, будьте на месте или оставьте ключ на вахте.\n\n{agent_name}, {unit}"),
    ("Other", "en", "Need more information",
     "Hello {student_name},\n\nThank you for your request {request_id}. To help you, could you please describe the "
     "problem in more detail and attach a screenshot or document if you have one?\n\n{agent_name}, {unit}"),
    ("Other", "ru", "Нужно больше информации",
     "Здравствуйте, {student_name}!\n\nСпасибо за обращение {request_id}. Чтобы помочь, опишите, пожалуйста, проблему "
     "подробнее и приложите скриншот или документ, если он есть.\n\n{agent_name}, {unit}"),
    ("Other", "kz", "Қосымша ақпарат керек",
     "Сәлеметсіз бе, {student_name}!\n\n{request_id} өтінішіңізге рахмет. Көмектесу үшін мәселені толығырақ сипаттап, "
     "скриншот немесе құжат болса тіркеңізші.\n\n{agent_name}, {unit}"),
    ("Library", "en", "Loan renewed",
     "Hello {student_name},\n\nI have renewed your loan for 14 more days and removed the late fee. You can renew online "
     "once more from your library account.\n\n{agent_name}, {unit}"),
    ("Academic", "en", "Grade appeal received",
     "Hello {student_name},\n\nYour grade appeal is registered. The appeal commission will review your work within 3 "
     "working days and you will receive the decision in this request.\n\n{agent_name}, {unit}"),
]

# Short resolution replies the demo generator posts per category and language (feed similar-case search).
CATEGORY_REPLIES: dict[str, dict[str, str]] = {
    "Academic": {"en": "The Dean's Office has registered your appeal; the commission will reply within 3 working days.",
                 "ru": "Деканат зарегистрировал вашу апелляцию, комиссия ответит в течение 3 рабочих дней.",
                 "kz": "Деканат апелляцияңызды тіркеді, комиссия 3 жұмыс күні ішінде жауап береді."},
    "Registration & Enrollment": {"en": "I have added you to the course section manually, please check your schedule now.",
                                  "ru": "Я вручную добавил(а) вас в секцию курса, проверьте расписание.",
                                  "kz": "Сізді курс секциясына қолмен қостым, кестеңізді тексеріңіз."},
    "Finance & Scholarships": {"en": "The payment has been processed, it should appear on your card within 24 hours.",
                               "ru": "Выплата проведена, деньги поступят на карту в течение 24 часов.",
                               "kz": "Төлем өткізілді, ақша 24 сағат ішінде картаңызға түседі."},
    "IT Support": {"en": "I have reset your password; please use the link sent to your university e-mail to log in.",
                   "ru": "Я сбросил(а) пароль, войдите по ссылке из письма на университетскую почту.",
                   "kz": "Құпиясөзді қалпына келтірдім, университет поштасына келген сілтеме арқылы кіріңіз."},
    "Dormitory & Housing": {"en": "A technician fixed the problem in your room today, please tell us if anything is still wrong.",
                            "ru": "Мастер сегодня устранил проблему в вашей комнате, напишите, если что-то ещё не так.",
                            "kz": "Шебер бүгін бөлмеңіздегі ақауды жөндеді, басқа мәселе болса жазыңыз."},
    "Documents & Certificates": {"en": "Your document is ready, please collect it at the Registrar Office with your student ID.",
                                 "ru": "Ваш документ готов, заберите его в Registrar Office со студенческим билетом.",
                                 "kz": "Құжатыңыз дайын, оны студенттік билетпен Registrar Office-тен алыңыз."},
    "Library": {"en": "I have renewed the loan for 14 days and removed the late fee.",
                "ru": "Я продлил(а) книгу на 14 дней и снял(а) штраф за просрочку.",
                "kz": "Кітапты 14 күнге ұзарттым және айыппұлды алып тастадым."},
    "Health & Wellbeing": {"en": "A counsellor will call you today; you can also walk in to the Medical Center any time.",
                           "ru": "Психолог свяжется с вами сегодня, также можно прийти в медцентр в любое время.",
                           "kz": "Психолог бүгін хабарласады, медорталыққа кез келген уақытта келуге болады."},
    "International Office": {"en": "We have prepared your visa support letter, it is attached to your student account.",
                             "ru": "Мы подготовили письмо визовой поддержки, оно в вашем личном кабинете.",
                             "kz": "Визалық қолдау хатын дайындадық, ол жеке кабинетіңізде."},
    "Other": {"en": "Thank you, we have forwarded your question to the responsible office.",
              "ru": "Спасибо, мы передали ваш вопрос в ответственный отдел.",
              "kz": "Рахмет, сұрағыңызды жауапты бөлімге жібердік."},
}
GREETING = {"en": "Hello {name},", "ru": "Здравствуйте, {name}!", "kz": "Сәлеметсіз бе, {name}!"}
