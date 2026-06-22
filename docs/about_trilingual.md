# About / Про проєкт / О проекте

*Author's statement for the Mariupol Urbicide Project. Source text written in Russian by Alexey Kovalev; adapted to the current iteration of the project and translated into English and Ukrainian.*

---

## РУССКИЙ (адаптированный исходник)

Я Алексей Ковалёв, журналист. 24 февраля 2022 года моя страна — Россия — вторглась в Украину. Помню, что первым моим ощущением был абсурд: ракеты, выпущенные моими соотечественниками, врезались в точно такие же дома и посреди точно таких же микрорайонов, как те, что окружали меня в Москве, — потому что их прототипы разрабатывались в одних и тех же советских архитектурных бюро.

Не сойти с ума от чудовищности происходящего мне помогала работа журналиста. Я брал интервью у жертв преступлений моей страны и у защитников Украины, редактировал репортажи коллег, писал собственные материалы о вторжении. Мне казалось: если я не смог это предотвратить, то мой моральный долг как россиянина — хотя бы помочь записать имена преступников с таким же красным паспортом, как у меня.

### О проекте

Первой жертвой моей страны — и зловеще точным предзнаменованием судьбы многих других украинских городов в последующие почти четыре года — стал Мариуполь. Сам я никогда не был в Украине, если не считать школьных каникул в Крыму. И в ту Украину, где был город Мариуполь, я уже не попаду никогда. Этот город до сих пор существует на карте мира лишь по привычке — как Бахмут, Северодонецк и другие города-призраки, один за другим уничтоженные армией моей страны.

С февраля по май 2022 года Мариуполь подвергался таким жестоким обстрелам, что кадры репортажей напоминали самые апокалиптические сражения Второй мировой. По разным оценкам, погибли десятки тысяч мирных жителей; точное число мы, возможно, не узнаем уже никогда. О масштабах одного из самых массовых убийств гражданского населения в отдельно взятом городе мы пока можем судить лишь по свежим могилам на Старокрымском кладбище, видным из космоса. А о том, что случилось и продолжает случаться с выжившими мариупольцами, рассказывает мой проект.

### Метод: бюрократическое саморазоблачение

Преступления России в Мариуполе не прекратились вместе с неприцельными ковровыми обстрелами густонаселённых жилых кварталов. Просто теперь это другие военные преступления — куда менее заметные и сильно растянутые во времени. Урбицид, убийство города, можно совершать и без бомбардировщиков и батарей залпового огня.

В конце 2022 года бюрократы оккупационной администрации деловито провели инвентаризацию уцелевшего жилого фонда, делая на полях пометки вроде «Дом полностью выгорел, во дворе труп, требуется уборка территории». Именно они составили и опубликовали список «объектов, пострадавших в результате боевых действий» и подлежащих сносу. И они же подписали приказы о сносе — часто ещё вполне целых многоэтажек и целых кварталов. Поэтому они такие же преступники, как командир дивизии, отдававший приказ обстреливать жилые кварталы.

Но снос — лишь одна из двух модальностей урбицида. Вторая, ещё более тихая, — это бюрократическое лишение собственности. Жильё уцелевших, но уехавших или погибших мариупольцев оккупационная администрация объявляет «бесхозяйным», вносит в реестр, проводит через оккупационные суды, занявшие место украинского правосудия, и передаёт новым владельцам. По подсчётам Human Rights Watch, через эти суды уже прошло около 8 100 таких дел. И здесь действует тот же принцип: каждое такое решение — это пронумерованное постановление, подписанное конкретным человеком.

В ходе расследования я столкнулся с парадоксом, который французский философ Жак Деррида называл «архивной лихорадкой», — иррациональной одержимостью преступника дотошной документацией собственных преступлений. Каждый снесённый дом — это конкретный приказ с конкретным номером. Каждое постановление, лишающее людей их родных руин, подписано конкретным человеком.

После работы в «Медузе», где с 2019 по 2022 год я возглавлял отдел расследований, я два года собирал материалы для будущих судебных дел о военных преступлениях как консультант по работе с открытыми источниками (OSINT) для Фонда справедливости Клуни (CFJ). Синтезировав этот опыт, я разработал собственную систему сбора доказательств. Пока она существует в виде экспериментального прототипа, но уже даёт осязаемые результаты. Система включает:

**Автоматизированный сбор доказательств.** Python-скрипты систематически собирают официальные документы с сайтов и других публичных ресурсов оккупационной администрации. Для каждого файла, ссылки и документа фиксируются SHA-256-хэш и таймстамп — это обеспечивает непрерывную цепочку хранения доказательств (chain of custody).

**Пространственно-временная база данных** на PostgreSQL/PostGIS хранит обогащённые из разных источников сведения о каждом объекте: административной единице, улице, доме, его правовом и физическом статусе на каждом этапе.

**Система нормализации.** Каждый адрес приводится ко всем возможным написаниям топонима (кириллицей по-русски и по-украински, латиницей в английской транскрипции) и к трём временным слоям (украинские топонимы до и после декоммунизации 2015–2016 годов и оккупационные переименования). Большинство адресов геокодированы через Google Maps API. Система распознаёт ошибки сканирования, смешение языков и искажённые написания.

**Конвейер перекрёстных ссылок.** Спутниковые снимки, официальные документы и оценки ущерба сводятся воедино и привязываются к конкретным объектам и конкретным виновным, образуя готовые пакеты доказательств — для исков о реституции в Реестр убытков Совета Европы и для уголовных дел по Римскому статуту.

Эти же нормализованные данные должны лечь в основу общедоступного ресурса, где вынужденно покинувшие город мариупольцы смогут найти свой адрес и узнать судьбу своего дома.

### Теоретическая основа

Работая над проектом, я опирался на концепции классиков критической теории:

- **«банальность зла» Ханны Арендт** — как бюрократические процедуры делают возможными массовые злодеяния;
- **«архивная лихорадка» Жака Деррида** — как навязчивое документирование оборачивается саморазоблачением;
- **«текучая современность» Зигмунта Баумана** — как бюрократия позволяет морально дистанцироваться от насилия;
- **«чрезвычайное положение» Джорджо Агамбена** — как оккупационное право создаёт зоны вне обычной правовой защиты.

### Правовая основа

Документация опирается на следующие нормы международного гуманитарного права:

- **Четвёртая Женевская конвенция, статья 53** — запрет уничтожения собственности без военной необходимости;
- **Гаагская конвенция (1907), статья 46** — защита частной собственности на оккупированной территории;
- **Римский статут, статья 8(2)(a)(iv)** — незаконное, бессмысленное и крупномасштабное уничтожение и присвоение имущества, не оправданное военной необходимостью;
- **Протокол Беркли** — стандарты работы с цифровыми доказательствами при расследовании нарушений прав человека.

---

## ENGLISH

I am Alexey Kovalev, a journalist. On 24 February 2022, my country — Russia — invaded Ukraine. My first reaction, I remember, was a sense of the absurd: missiles fired by my own countrymen were slamming into buildings exactly like the ones around me in Moscow, in the middle of neighbourhoods exactly like mine — because their blueprints came from the same Soviet architectural bureaus.

What kept me from losing my mind to the monstrousness of it was the work of a journalist. I interviewed victims of my country's crimes and defenders of Ukraine, edited my colleagues' dispatches, wrote my own reporting on the invasion. It seemed to me that if I could not prevent this, then my moral duty as a Russian was at least to help record the names of the criminals who carry the same red passport as I do.

### About the project

The first victim of my country — and an ominously precise omen of what would befall many other Ukrainian cities over the next nearly four years — was Mariupol. I have never been to Ukraine myself, apart from school holidays in Crimea. And the Ukraine in which the city of Mariupol existed, I will never reach now. That city still appears on the map of the world only out of habit — like Bakhmut, Sieverodonetsk, and the other ghost towns destroyed one after another by my country's army.

From February to May 2022, Mariupol was shelled so savagely that the footage looked like the most apocalyptic battles of the Second World War. By various estimates, tens of thousands of civilians were killed; the exact number we may never know. The scale of one of the largest mass killings of the civilian population of a single city can still only be gauged from the fresh graves at Starokrymske cemetery, visible from space. What happened — and is still happening — to the Mariupol residents who survived is what this project sets out to document.

### Method: bureaucratic self-incrimination

Russia's crimes in Mariupol did not end when the indiscriminate carpet shelling of densely populated residential districts stopped. They simply became different war crimes — far less visible, and stretched out over time. Urbicide, the killing of a city, can be carried out without bombers or multiple-rocket batteries.

At the end of 2022, the bureaucrats of the occupation administration briskly inventoried the surviving housing stock, jotting notes in the margins like "building completely burned out, corpse in the courtyard, site clearance required." It was they who compiled and published the list of "objects damaged as a result of combat operations" slated for demolition. And it was they who signed the demolition orders — often for apartment blocks and entire neighbourhoods that were still largely intact. That makes them every bit as culpable as the divisional commander who gave the order to shell residential quarters.

But demolition is only one of the two modes of this urbicide. The second, quieter one is dispossession by paperwork. The homes of Mariupol residents who survived but had fled, or who were killed, are declared "ownerless" (*bezkhozyaynaya*) by the occupation administration, entered into a registry, passed through the occupation courts that have taken the place of Ukrainian justice, and handed to new owners. By Human Rights Watch's count, roughly 8,100 such cases have already moved through those courts. The same principle holds here: every one of these rulings is a numbered decree, signed by a named individual.

In the course of this investigation I ran into a paradox that the French philosopher Jacques Derrida called "archive fever" — the perpetrator's wholly irrational compulsion to document his own crimes in meticulous detail. Every demolished house is a specific order with a specific number. Every decree stripping people of their own ruins bears a specific person's signature.

After Meduza — where from 2019 to 2022 I headed the investigations desk — I spent two years gathering material for future war-crimes cases as an open-source (OSINT) consultant for the Clooney Foundation for Justice (CFJ). Drawing those threads together, I built my own evidence-collection system. For now it is an experimental prototype, but it already yields tangible results. The system comprises:

**Automated evidence collection.** Python scripts systematically harvest official documents from the websites and other public resources of the occupation administration. For every file, link, and document, a SHA-256 hash and a timestamp are recorded — establishing an unbroken chain of custody.

**A spatiotemporal PostgreSQL/PostGIS database** holds source-enriched data on each property: its administrative unit, street, building, and its legal and physical status at every stage of its life.

**A normalisation layer.** Every address is reconciled across all plausible spellings of each toponym (Cyrillic in Russian and Ukrainian, Latin in English transcription) and across three temporal layers (Ukrainian toponyms before and after the 2015–2016 decommunisation, and the occupation-era renamings). Most addresses are geocoded via the Google Maps API. The system also catches scanning errors, mixed-language strings, and corrupted spellings.

**A cross-referencing pipeline.** Satellite imagery, official documents, and damage assessments are drawn together and tied to specific properties and specific perpetrators, forming court-ready evidence packages — for restitution claims to the Council of Europe's Register of Damage and for criminal proceedings under the Rome Statute.

The same normalised data is meant to underpin a public resource where displaced Mariupol residents can look up their own address and learn the fate of their home.

### Theoretical grounding

In this work I have drawn on ideas formulated by the classics of critical theory:

- **Hannah Arendt's "banality of evil"** — how bureaucratic procedure makes mass atrocity possible;
- **Jacques Derrida's "archive fever"** — how compulsive documentation becomes self-incrimination;
- **Zygmunt Bauman's "liquid modernity"** — how bureaucracy enables moral distance from violence;
- **Giorgio Agamben's "state of exception"** — how occupation law creates zones beyond ordinary legal protection.

### Legal grounding

The documentation is anchored in the following provisions of international humanitarian law:

- **Fourth Geneva Convention, Article 53** — prohibiting the destruction of property without military necessity;
- **Hague Convention (1907), Article 46** — protecting private property under occupation;
- **Rome Statute, Article 8(2)(a)(iv)** — the unlawful, wanton, and large-scale destruction and appropriation of property not justified by military necessity;
- **Berkeley Protocol** — standards for handling digital evidence in human rights investigations.

---

## УКРАЇНСЬКОЮ

Я Олексій Ковальов, журналіст. 24 лютого 2022 року моя країна — Росія — вторглася в Україну. Пам'ятаю, що першим моїм відчуттям був абсурд: ракети, випущені моїми співвітчизниками, влучали в точно такі самі будинки й посеред точно таких самих мікрорайонів, як ті, що оточували мене в Москві, — бо їхні прототипи розробляли ті самі радянські архітектурні бюро.

Не збожеволіти від жахіття того, що відбувалося, мені допомагала журналістська робота. Я брав інтерв'ю у жертв злочинів моєї країни та в захисників України, редагував репортажі колег, писав власні матеріали про вторгнення. Мені здавалося: якщо я не зміг цьому запобігти, то мій моральний обов'язок як росіянина — бодай допомогти записати імена злочинців із таким самим червоним паспортом, як у мене.

### Про проєкт

Першою жертвою моєї країни — і моторошно точним провістям долі багатьох інших українських міст у наступні майже чотири роки — став Маріуполь. Сам я ніколи не був в Україні, якщо не рахувати шкільних канікул у Криму. І до тієї України, де було місто Маріуполь, я вже не потраплю ніколи. Це місто досі існує на карті світу лише за звичкою — як Бахмут, Сєвєродонецьк та інші міста-привиди, знищені одне за одним армією моєї країни.

З лютого по травень 2022 року Маріуполь зазнавав таких жорстоких обстрілів, що кадри репортажів нагадували найбільш апокаліптичні битви Другої світової. За різними оцінками, загинули десятки тисяч мирних жителів; точного числа ми, можливо, не дізнаємося вже ніколи. Про масштаб одного з наймасовіших убивств цивільного населення окремо взятого міста ми поки що можемо судити лише з нових могил на Старокримському кладовищі, помітних із космосу. А про те, що сталося — і досі стається — з уцілілими маріупольцями, розповідає мій проєкт.

### Метод: бюрократичне самовикриття

Злочини Росії в Маріуполі не припинилися разом із неприцільними килимовими обстрілами густонаселених житлових кварталів. Просто тепер це інші воєнні злочини — куди менш помітні й сильно розтягнуті в часі. Урбіцид, убивство міста, можна чинити й без бомбардувальників та батарей залпового вогню.

Наприкінці 2022 року бюрократи окупаційної адміністрації заклопотано провели інвентаризацію вцілілого житлового фонду, роблячи на полях помітки на кшталт «Будинок повністю вигорів, у дворі труп, потрібне прибирання території». Саме вони склали й оприлюднили перелік «об'єктів, що постраждали внаслідок бойових дій» і підлягають знесенню. І саме вони підписали накази про знесення — часто ще цілком цілих багатоповерхівок і цілих кварталів. Тому вони такі самі злочинці, як командир дивізії, що віддавав наказ обстрілювати житлові квартали.

Але знесення — лише одна з двох модальностей урбіциду. Друга, ще тихіша, — це бюрократичне позбавлення власності. Житло маріупольців, які вціліли, але виїхали з міста або загинули, окупаційна адміністрація оголошує «безхазяйним» (рос. «бесхозяйная»), вносить до реєстру, проводить через окупаційні суди, що посіли місце українського правосуддя, і передає новим власникам. За підрахунками Human Rights Watch, через ці суди вже пройшло близько 8 100 таких справ. І тут діє той самий принцип: кожне таке рішення — це пронумерована постанова, підписана конкретною людиною.

Під час розслідування я зіткнувся з парадоксом, який французький філософ Жак Дерріда називав «архівною гарячкою», — ірраціональною одержимістю злочинця ретельним документуванням власних злочинів. Кожен знесений будинок — це конкретний наказ із конкретним номером. Кожна постанова, що позбавляє людей їхніх рідних руїн, підписана конкретною людиною.

Після роботи в «Медузі», де з 2019 по 2022 рік я очолював відділ розслідувань, я два роки збирав матеріали для майбутніх судових справ про воєнні злочини як консультант з роботи з відкритими джерелами (OSINT) для Фонду справедливості Клуні (CFJ). Спираючись на цей досвід, я розробив власну систему збору доказів. Поки вона існує як експериментальний прототип, але вже дає відчутні результати. Система охоплює:

**Автоматизований збір доказів.** Python-скрипти систематично збирають офіційні документи із сайтів та інших публічних ресурсів окупаційної адміністрації. Для кожного файлу, посилання й документа фіксуються SHA-256-хеш і часова позначка — це забезпечує безперервний ланцюг зберігання доказів (chain of custody).

**Просторово-часова база даних** на PostgreSQL/PostGIS зберігає збагачені з різних джерел відомості про кожен об'єкт: адміністративну одиницю, вулицю, будинок, його правовий і фізичний статус на кожному етапі.

**Система нормалізації.** Кожну адресу зведено до всіх можливих написань топоніма (кирилицею російською та українською, латиницею в англійській транскрипції) і до трьох часових шарів (українські топоніми до та після декомунізації 2015–2016 років і окупаційні перейменування). Більшість адрес геокодовано через Google Maps API. Система розпізнає помилки сканування, змішування мов та спотворені написання.

**Конвеєр перехресних посилань.** Супутникові знімки, офіційні документи й оцінки збитків зводяться докупи та прив'язуються до конкретних об'єктів і конкретних винуватців, утворюючи готові пакети доказів — для позовів про реституцію до Реєстру збитків Ради Європи та для кримінальних справ за Римським статутом.

Ці самі нормалізовані дані мають лягти в основу загальнодоступного ресурсу, де вимушено переселені маріупольці зможуть знайти свою адресу й дізнатися про долю свого дому.

### Теоретичне підґрунтя

Працюючи над проєктом, я спирався на концепції класиків критичної теорії:

- **«банальність зла» Ганни Арендт** — як бюрократичні процедури уможливлюють масові злодіяння;
- **«архівна гарячка» Жака Дерріди** — як нав'язливе документування обертається самовикриттям;
- **«плинна сучасність» Зиґмунта Баумана** — як бюрократія дозволяє морально дистанціюватися від насильства;
- **«надзвичайний стан» Джорджо Аґамбена** — як окупаційне право створює зони поза звичайним правовим захистом.

### Правове підґрунтя

Документація спирається на такі норми міжнародного гуманітарного права:

- **Четверта Женевська конвенція, стаття 53** — заборона знищення власності без воєнної необхідності;
- **Гаазька конвенція (1907), стаття 46** — захист приватної власності на окупованій території;
- **Римський статут, стаття 8(2)(a)(iv)** — незаконне, безглузде й широкомасштабне знищення та привласнення майна, не виправдане воєнною необхідністю;
- **Протокол Берклі** — стандарти роботи з цифровими доказами під час розслідування порушень прав людини.
