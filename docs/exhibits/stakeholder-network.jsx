import React, { useState, useMemo, useRef, useCallback, useEffect } from "react";

// ============================================================================
// SOURCE OF TRUTH: stakeholder_nodes.jsonl + stakeholder_edges.jsonl (embedded)
// ============================================================================
const NETWORK = {"nodes":[{"node_id":"instr:ownerless_decree","kind":"instrument_class","canonical_name":"Ownerless decrees (rung A)","tier":"pipeline"},{"node_id":"instr:demolition_decree","kind":"instrument_class","canonical_name":"Demolition decrees (rung C)","tier":"pipeline"},{"node_id":"instr:court_proceedings","kind":"instrument_class","canonical_name":"Особое-производство transfers (rung B)","tier":"pipeline"},{"node_id":"instr:dnr_land_order","kind":"instrument_class","canonical_name":"DNR land-reallocation orders (rung D)","tier":"pipeline"},{"node_id":"instr:reconstruction","kind":"instrument_class","canonical_name":"Federal reconstruction contracts (rung E)","tier":"pipeline"},{"node_id":"instr:dnr_normative_act","kind":"instrument_class","canonical_name":"DNR normative acts (framework)","tier":"pipeline"},{"node_id":"person:кольцов-а-в","kind":"person","canonical_name":"Кольцов А.В.","tier":"municipal","roles":["signing_official"],"org":"Администрация городского округа Мариуполь","evidence":["ownerless_decrees.jsonl","demolition_decrees.jsonl"],"name_variants":["А.В. Кольцов"]},{"node_id":"person:моргун-о-в","kind":"person","canonical_name":"Моргун О.В.","tier":"municipal","roles":["signing_official"],"org":"Администрация городского округа Мариуполь","evidence":["ownerless_decrees.jsonl","demolition_decrees.jsonl"],"name_variants":["О.В. Моргун"]},{"node_id":"person:дмитриев-а-в","kind":"person","canonical_name":"Дмитриев А.В.","tier":"municipal","roles":["signing_official","commission_member"],"org":"Администрация городского округа Мариуполь","evidence":["ownerless_decrees.jsonl","demolition_decrees.jsonl"],"name_variants":["А.В. Дмитриев"]},{"node_id":"person:краснолуцкая-т-ю","kind":"person","canonical_name":"Краснолуцкая Т.Ю.","tier":"municipal","roles":["signing_official"],"org":"Администрация городского округа Мариуполь","evidence":["ownerless_decrees.jsonl"],"name_variants":["Т.Ю. Краснолуцкая"]},{"node_id":"person:перепечай-б-н","kind":"person","canonical_name":"Перепечай Б.Н.","tier":"municipal","roles":["signing_official"],"org":"Администрация городского округа Мариуполь","evidence":["ownerless_decrees.jsonl"],"name_variants":["Б.Н. Перепечай"]},{"node_id":"person:матейко-в-а","kind":"person","canonical_name":"Матейко В.А.","tier":"municipal","roles":["signing_official"],"org":"Администрация городского округа Мариуполь","evidence":["ownerless_decrees.jsonl"],"name_variants":["В.А. Матейко"]},{"node_id":"person:цыба-л-в","kind":"person","canonical_name":"Цыба Л.В.","tier":"municipal","roles":["commission_member"],"org":"Администрация городского округа Мариуполь","evidence":["demolition_decrees.jsonl"]},{"node_id":"person:лысенко-м-г","kind":"person","canonical_name":"Лысенко М.Г.","tier":"municipal","roles":["commission_member"],"org":"Администрация городского округа Мариуполь","evidence":["demolition_decrees.jsonl"]},{"node_id":"person:мирошниченко-я-с","kind":"person","canonical_name":"Мирошниченко Я.С.","tier":"municipal","roles":["commission_member"],"org":"Администрация городского округа Мариуполь","evidence":["demolition_decrees.jsonl"]},{"node_id":"person:хараджа-о-с","kind":"person","canonical_name":"Хараджа О.С.","tier":"municipal","roles":["commission_member"],"org":"Администрация городского округа Мариуполь","evidence":["demolition_decrees.jsonl"]},{"node_id":"person:кирьякулова-о-в","kind":"person","canonical_name":"Кирьякулова О.В.","tier":"municipal","roles":["commission_member"],"org":"Администрация городского округа Мариуполь","evidence":["demolition_decrees.jsonl"]},{"node_id":"person:клисак-н-а","kind":"person","canonical_name":"Клисак Н.А.","tier":"municipal","roles":["commission_member"],"org":"Администрация городского округа Мариуполь","evidence":["demolition_decrees.jsonl"]},{"node_id":"person:хаджинов-д-м","kind":"person","canonical_name":"Хаджинов Д.М.","tier":"municipal","roles":["commission_member"],"org":"МУП «Коммунальник»","evidence":["demolition_decrees.jsonl"]},{"node_id":"person:овсиенко-и-а","kind":"person","canonical_name":"Овсиенко И.А.","tier":"municipal","roles":["commission_member"],"org":"Администрация городского округа Мариуполь","evidence":["demolition_decrees.jsonl"]},{"node_id":"person:пушилин-д-в","kind":"person","canonical_name":"Пушилин Д.В.","tier":"dnr","roles":["signing_official"],"org":"Глава ДНР","evidence":["dnr_land_orders.jsonl"],"name_variants":["Д. В. Пушилин"]},{"node_id":"org:порфир","kind":"org","canonical_name":"Специализированный застройщик-1 «Порфир»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"inn":"9310009271","ogrn":"1239300008870"},{"node_id":"org:сгм-монтаж","kind":"org","canonical_name":"СГМ МОНТАЖ","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"name_variants":["ООО \"СГМ МОНТАЖ\""],"inn":"9310018029","ogrn":"1259300002719","address":"Донецкая Народная Республика, Г. МАРИУПОЛЬ, ПР-КТ СТРОИТЕЛЕЙ, Д. 136А, ПОМЕЩ. 10"},{"node_id":"org:олимпстрой-нр","kind":"org","canonical_name":"Специализированный застройщик «Олимпстрой НР»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"name_variants":["ООО \"СПЕЦИАЛИЗИРОВАННЫЙ ЗАСТРОЙЩИК ОЛИМПСТРОЙ НР\""],"inn":"9309027678","ogrn":"1249300011058","address":"Донецкая Народная Республика, Г. ДОНЕЦК, ПЛ. ИМЕНИ ГЕРОЯ РОССИИ НУРМАГОМЕДА ГАДЖИМАГОМЕДОВА, Д. 1"},{"node_id":"org:эверест-домостроение","kind":"org","canonical_name":"ЭВЕРЕСТ ДОМОСТРОЕНИЕ","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"name_variants":["АО \"ЭВЕРЕСТ ДОМОСТРОЕНИЕ\""],"inn":"9303042743","ogrn":"1269300001354","address":"Донецкая Народная Республика, Г. ДОНЕЦК, УЛ. МАРЬИНСКАЯ, Д. 1"},{"node_id":"org:строительное-управление-2007","kind":"org","canonical_name":"Специализированный застройщик «Строительное управление-2007»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"inn":"9310008599","ogrn":"1239300007000"},{"node_id":"org:мирастрой-3","kind":"org","canonical_name":"Специализированный застройщик «МираСтрой 3»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"name_variants":["ООО \"СЗ \"МИРАСТРОЙ 3\""],"inn":"9303036524","ogrn":"1249300004821","address":"Донецкая Народная Республика, Г. МАРИУПОЛЬ, УЛ. ЭНГЕЛЬСА, Д. 26/2"},{"node_id":"org:мирастрой-4","kind":"org","canonical_name":"Специализированный застройщик «МираСтрой 4»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"inn":"9303036531"},{"node_id":"org:новое-время-3","kind":"org","canonical_name":"Специализированный застройщик «НОВОЕ ВРЕМЯ 3»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"name_variants":["ООО СЗ \"НОВОЕ ВРЕМЯ 3\""],"inn":"9309028294","ogrn":"1249300016536","address":"Донецкая Народная Республика, Г. ДОНЕЦК, УЛ. МОЛОДЫХ ШАХТЁРОВ, Д. 37"},{"node_id":"org:корпорация-сму-5","kind":"org","canonical_name":"Специализированный застройщик «Корпорация СМУ-5»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"inn":"9310017508"},{"node_id":"org:эводом-5","kind":"org","canonical_name":"СПЕЦИАЛИЗИРОВАННЫЙ ЗАСТРОЙЩИК «ЭВОДОМ-5»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"name_variants":["Специализированный застройщик «Эводом-5»"],"inn":"9303038232"},{"node_id":"org:солнечная","kind":"org","canonical_name":"Специализированный застройщик Солнечная","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"inn":"9311026992"},{"node_id":"org:строительное-управление-2007-инвест","kind":"org","canonical_name":"Специализированный застройщик «Строительное управление — 2007 Инвест»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl"],"name_variants":["Специализированный застройщик «Строительное управление-2007 Инвест»"],"inn":"9310015807"},{"node_id":"org:региональная-строительная-компания","kind":"org","canonical_name":"Региональная строительная компания","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"inn":"9309026106"},{"node_id":"org:сириус-билд","kind":"org","canonical_name":"Специализированный застройщик «СИРИУС БИЛД»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"inn":"9310014320"},{"node_id":"org:антарес","kind":"org","canonical_name":"Специализированный застройщик «Антарес»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"inn":"9310014480"},{"node_id":"org:восход","kind":"org","canonical_name":"Специализированный застройщик «Восход»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"inn":"9310013976"},{"node_id":"org:осс","kind":"org","canonical_name":"ОСС","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl"]},{"node_id":"org:ркс-девелопмент","kind":"org","canonical_name":"Специализированный застройщик «РКС-Девелопмент»","tier":"commercial","roles":["developer"],"evidence":["dnr_land_orders.jsonl","egrul_inn_lookups.jsonl"],"name_variants":["ООО СЗ \"РКС-ДЕВЕЛОПМЕНТ\""],"inn":"9310007980","ogrn":"1239300005526","address":"Донецкая Народная Республика, Г. МАРИУПОЛЬ, ПР-КТ МЕТАЛЛУРГОВ, Д. 54А, ПОМЕЩ. 9"},{"node_id":"org:единый-заказчик","kind":"org","canonical_name":"ППК \"Единый заказчик\"","tier":"federal","roles":["responsible_executor"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:гк-трансстройинвест","kind":"org","canonical_name":"ГК Трансстройинвест","tier":"federal","roles":["contractor"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:гк-екс","kind":"org","canonical_name":"ГК \"ЕКС\"","tier":"federal","roles":["contractor"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:крост","kind":"org","canonical_name":"Крост","tier":"federal","roles":["contractor"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:московская-область","kind":"org","canonical_name":"Московская область","tier":"federal","roles":["shef_region"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:крокус-групп","kind":"org","canonical_name":"Крокус Групп","tier":"federal","roles":["contractor"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:тульская-область","kind":"org","canonical_name":"Тульская область","tier":"federal","roles":["shef_region"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:ук-новый-капитал","kind":"org","canonical_name":"АО \"УК Новый Капитал\"","tier":"federal","roles":["contractor"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:пск-строймонолит","kind":"org","canonical_name":"ПСК Строймонолит","tier":"federal","roles":["contractor"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:спецснабтранс","kind":"org","canonical_name":"Спецснабтранс","tier":"federal","roles":["contractor"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:московский-политех","kind":"org","canonical_name":"Московский политех","tier":"federal","roles":["contractor"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:монотек-строй","kind":"org","canonical_name":"ООО \"Монотек Строй\"","tier":"federal","roles":["contractor"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:интеко","kind":"org","canonical_name":"АО \"ИНТЕКО\"","tier":"federal","roles":["contractor"],"evidence":["damage_assessment.jsonl"]},{"node_id":"org:комитет-по-тарифам-донецкой-народной-республики","kind":"org","canonical_name":"Комитет по тарифам Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:правительство-донецкой-народной-республики","kind":"org","canonical_name":"Правительство Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:глава-донецкой-народной-республики","kind":"org","canonical_name":"Глава Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:министерство-строительства-архитектуры-и-жилищно-коммунального-хозяйства-донецкой-народной-республики","kind":"org","canonical_name":"Министерство строительства, архитектуры и жилищно-коммунального хозяйства Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:донецкая-народная-республика","kind":"org","canonical_name":"Донецкая Народная Республика","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:министерство-спорта-и-туризма-донецкой-народной-республики","kind":"org","canonical_name":"Министерство спорта и туризма Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:министерство-имущественных-и-земельных-отношений-донецкой-народной-республики","kind":"org","canonical_name":"Министерство имущественных и земельных отношений Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority","petitioner"],"evidence":["pravo_region80_relevant.jsonl","postgres:court_case/actor"],"name_variants":["Министерство имущественных земельных отношений Донецкой Народной Республики","Министрерство имущественных и земельных отношений ДНР","Министерство имущественных и земельных отношений ДНР"]},{"node_id":"org:министерство-культуры-донецкой-народной-республики","kind":"org","canonical_name":"Министерство культуры Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:министерство-природных-ресурсов-и-экологии-донецкой-народной-республики","kind":"org","canonical_name":"Министерство природных ресурсов и экологии Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:министерство-образования-и-науки-донецкой-народной-республики","kind":"org","canonical_name":"Министерство образования и науки Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:министерство-промышленности-и-торговли-донецкой-народной-республики","kind":"org","canonical_name":"Министерство промышленности и торговли Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:республиканская-служба-по-тарифам-донецкой-народной-республики","kind":"org","canonical_name":"Республиканская служба по тарифам Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:министерство-труда-и-социальной-политики-донецкой-народной-республики","kind":"org","canonical_name":"Министерство труда и социальной политики Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:главное-управления-геологии-и-геоэкологии-донецкой-народной-республики","kind":"org","canonical_name":"Главное управления геологии и геоэкологии Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:фонд-государственного-имущества-донецкой-народной-республики","kind":"org","canonical_name":"Фонд государственного имущества Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority","petitioner"],"evidence":["pravo_region80_relevant.jsonl","postgres:court_case/actor"],"name_variants":["Фонд государственного имущества","ФГИ ДНР","Фонд государственного имущества ДНР"]},{"node_id":"org:государственный-комитет-по-земельным-ресурсам-донецкой-народной-республики","kind":"org","canonical_name":"Государственный комитет по земельным ресурсам Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"org:министерство-строительства-и-жилищно-коммунального-хозяйства-донецкой-народной-республики","kind":"org","canonical_name":"Министерство строительства и жилищно-коммунального хозяйства Донецкой Народной Республики","tier":"dnr","roles":["signatory_authority"],"evidence":["pravo_region80_relevant.jsonl"]},{"node_id":"person:харламова-т-с","kind":"person","canonical_name":"Харламова Т.С.","tier":"commercial","roles":["director"],"evidence":["egrul_inn_lookups.jsonl"],"name_variants":["ХАРЛАМОВА ТАТЬЯНА СЕРГЕЕВНА"]},{"node_id":"person:василенко-и-и","kind":"person","canonical_name":"Василенко И.И.","tier":"commercial","roles":["director"],"evidence":["egrul_inn_lookups.jsonl"],"name_variants":["ВАСИЛЕНКО ИГОРЬ ИГОРЕВИЧ"]},{"node_id":"person:митин-с-в","kind":"person","canonical_name":"Митин С.В.","tier":"commercial","roles":["director"],"evidence":["egrul_inn_lookups.jsonl"],"name_variants":["МИТИН СЕРГЕЙ ВАЛЕРИЕВИЧ"]},{"node_id":"person:сарибекян-а-в","kind":"person","canonical_name":"Сарибекян А.В.","tier":"commercial","roles":["director"],"evidence":["egrul_inn_lookups.jsonl"],"name_variants":["САРИБЕКЯН АВЕТИК ВОЛОДЯЕВИЧ"]},{"node_id":"person:попченко-в-г","kind":"person","canonical_name":"Попченко В.Г.","tier":"commercial","roles":["director"],"evidence":["egrul_inn_lookups.jsonl"],"name_variants":["ПОПЧЕНКО ВАДИМ ГЕННАДЬЕВИЧ"]},{"node_id":"org:су-2007-инвест","kind":"org","canonical_name":"ООО \"СЗ \"СУ-2007 ИНВЕСТ\"","tier":"commercial","roles":["developer"],"evidence":["egrul_inn_lookups.jsonl"],"inn":"9310015807","ogrn":"1249300015249","address":"Донецкая Народная Республика, Г. МАРИУПОЛЬ, ПР-КТ МЕТАЛЛУРГОВ, Д. 87А, ПОМЕЩ. 5"},{"node_id":"person:крючков-а-м","kind":"person","canonical_name":"Крючков А.М.","tier":"commercial","roles":["director"],"evidence":["egrul_inn_lookups.jsonl"],"name_variants":["КРЮЧКОВ АЛЕКСЕЙ МАТВЕЕВИЧ"]},{"node_id":"person:лопухов-к-к","kind":"person","canonical_name":"Лопухов К.К.","tier":"commercial","roles":["director"],"evidence":["egrul_inn_lookups.jsonl"],"name_variants":["ЛОПУХОВ КОНСТАНТИН КОНСТАНТИНОВИЧ"]},{"node_id":"org:военно-строительная-компания","kind":"org","canonical_name":"ППК «Военно-строительная компания»","tier":"federal","roles":["contractor"],"evidence":["open_source_investigations.jsonl"],"name_variants":["ВСК","VSK","vskmo.ru"]},{"node_id":"org:олимпситистрой","kind":"org","canonical_name":"ООО «Олимпситистрой»","tier":"commercial","roles":["contractor"],"evidence":["open_source_investigations.jsonl"],"name_variants":["Olimpsitistroy","ОлимпСитиСтрой"],"inn":"7719585979","ogrn":"1067746433204","address":"Москва, Нагатинская ул., д. 2"},{"node_id":"org:оборонспецстрой","kind":"org","canonical_name":"ООО «Оборонспецстрой»","tier":"commercial","roles":["developer"],"evidence":["open_source_investigations.jsonl"],"name_variants":["Oboronspetsstroy"],"inn":"7734691114","ogrn":"1127747177887"},{"node_id":"person:хавронин-д-а","kind":"person","canonical_name":"Хавронин Д.А.","tier":"commercial","roles":["founder"],"org":"ООО «Олимпситистрой»","evidence":["open_source_investigations.jsonl"],"name_variants":["Дмитрий Александрович Хавронин"]},{"node_id":"person:фомин-а-г","kind":"person","canonical_name":"Фомин А.Г.","tier":"commercial","roles":["founder"],"org":"ООО «Олимпситистрой»","evidence":["open_source_investigations.jsonl"],"name_variants":["Александр Григорьевич Фомин"]},{"node_id":"person:иванов-т-в","kind":"person","canonical_name":"Иванов Т.В.","tier":"federal","roles":["patron"],"evidence":["open_source_investigations.jsonl"],"name_variants":["Тимур Вадимович Иванов","Timur Ivanov"]},{"node_id":"person:сазонова-ю-ю","kind":"person","canonical_name":"Сазонова Ю.Ю.","tier":"judicial","roles":["judge"],"org":"zhovtnevy_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Сазонова Юлия Юрьевна"]},{"node_id":"person:маркова-е-в","kind":"person","canonical_name":"Маркова Е.В.","tier":"judicial","roles":["judge"],"org":"ilyichevsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Маркова Елена Владимировна"]},{"node_id":"person:гревцова-в-а","kind":"person","canonical_name":"Гревцова В.А.","tier":"judicial","roles":["judge"],"org":"primorsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Гревцова Виктория Алексеевна"]},{"node_id":"person:нидзиева-н-н","kind":"person","canonical_name":"Нидзиева Н.Н.","tier":"judicial","roles":["judge"],"org":"primorsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Нидзиева Наталья Николаевна"]},{"node_id":"person:леонов-а-ю","kind":"person","canonical_name":"Леонов А.Ю.","tier":"judicial","roles":["judge"],"org":"zhovtnevy_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Леонов Александр Юрьевич"]},{"node_id":"person:кенжегарина-д-м","kind":"person","canonical_name":"Кенжегарина Д.М.","tier":"judicial","roles":["judge"],"org":"zhovtnevy_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Кенжегарина Даметкен Максутовна"]},{"node_id":"person:ремпе-м-в","kind":"person","canonical_name":"Ремпе М.В.","tier":"judicial","roles":["judge"],"org":"ordzhonikidzevsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Ремпе Мария Васильевна"]},{"node_id":"person:таубаева-а-у","kind":"person","canonical_name":"Таубаева А.У.","tier":"judicial","roles":["judge"],"org":"zhovtnevy_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Таубаева Айжан Умырзаговна"]},{"node_id":"person:струнов-н-и","kind":"person","canonical_name":"Струнов Н.И.","tier":"judicial","roles":["judge"],"org":"zhovtnevy_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Струнов Никита Иванович"]},{"node_id":"person:митерев-э-е","kind":"person","canonical_name":"Митерев Э.Е.","tier":"judicial","roles":["judge"],"org":"ordzhonikidzevsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Митерев Эльдар Евгеньевич"]},{"node_id":"person:мяконькая-т-а","kind":"person","canonical_name":"Мяконькая Т.А.","tier":"judicial","roles":["judge"],"org":"zhovtnevy_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Мяконькая Татьяна Александровна"]},{"node_id":"person:кралинина-н-г","kind":"person","canonical_name":"Кралинина Н.Г.","tier":"judicial","roles":["judge"],"org":"zhovtnevy_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Кралинина Наталья Геннадьевна"]},{"node_id":"person:романов-д-с","kind":"person","canonical_name":"Романов Д.С.","tier":"judicial","roles":["judge"],"org":"zhovtnevy_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Романов Дмитрий Сергеевич"]},{"node_id":"person:дулькина-н-в","kind":"person","canonical_name":"Дулькина Н.В.","tier":"judicial","roles":["judge"],"org":"zhovtnevy_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Дулькина Наталия Викторовна"]},{"node_id":"person:сахапова-р-р","kind":"person","canonical_name":"Сахапова Р.Р.","tier":"judicial","roles":["judge"],"org":"ordzhonikidzevsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Сахапова Рената Рамилевна"]},{"node_id":"person:бойко-в-о","kind":"person","canonical_name":"Бойко В.О.","tier":"judicial","roles":["judge"],"org":"primorsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Бойко Виктория Олеговна"]},{"node_id":"person:ахтямова-э-с","kind":"person","canonical_name":"Ахтямова Э.С.","tier":"judicial","roles":["judge"],"org":"ordzhonikidzevsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Ахтямова Эльвира Саматовна"]},{"node_id":"person:степанова-е-в","kind":"person","canonical_name":"Степанова Е.В.","tier":"judicial","roles":["judge"],"org":"ilyichevsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Степанова Екатерина Васильевна"]},{"node_id":"person:логвинов-о-в","kind":"person","canonical_name":"Логвинов О.В.","tier":"judicial","roles":["judge"],"org":"ilyichevsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Логвинов Олег Валентинович"]},{"node_id":"person:белоусов-п-в","kind":"person","canonical_name":"Белоусов П.В.","tier":"judicial","roles":["judge"],"org":"zhovtnevy_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Белоусов Павел Валериевич"]},{"node_id":"person:тлеужанова-б-е","kind":"person","canonical_name":"Тлеужанова Б.Е.","tier":"judicial","roles":["judge"],"org":"primorsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Тлеужанова Ботагоз Елеусизовна"]},{"node_id":"person:гузаирова-э-и","kind":"person","canonical_name":"Гузаирова Э.И.","tier":"judicial","roles":["judge"],"org":"zhovtnevy_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Гузаирова Эльвира Ильдаровна"]},{"node_id":"person:павленко-д-к","kind":"person","canonical_name":"Павленко Д.К.","tier":"judicial","roles":["judge"],"org":"ordzhonikidzevsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Павленко Денис Константинович"]},{"node_id":"person:резниченко-в-а","kind":"person","canonical_name":"Резниченко В.А.","tier":"judicial","roles":["judge"],"org":"primorsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Резниченко Владимир Алексеевич"]},{"node_id":"person:климова-с-ю","kind":"person","canonical_name":"Климова С.Ю.","tier":"judicial","roles":["judge"],"org":"ordzhonikidzevsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Климова Светлана Юрьевна"]},{"node_id":"person:головченко-ю-н","kind":"person","canonical_name":"Головченко Ю.Н.","tier":"judicial","roles":["judge"],"org":"ilyichevsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Головченко Юлия Николаевна"]},{"node_id":"person:гаврилюк-е-а","kind":"person","canonical_name":"Гаврилюк Е.А.","tier":"judicial","roles":["judge"],"org":"ordzhonikidzevsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Гаврилюк Евгения Анатольевна"]},{"node_id":"person:мартынов-а-а","kind":"person","canonical_name":"Мартынов А.А.","tier":"judicial","roles":["judge"],"org":"ilyichevsky_mariupol","evidence":["postgres:court_case/actor"],"name_variants":["Мартынов Александр Анатольевич"]},{"node_id":"org:министерство-строительства-и-жкх-донецкой-народной-республики","kind":"org","canonical_name":"Министерство строительства и ЖКХ Донецкой Народной Республики","tier":"dnr","roles":["petitioner"],"evidence":["postgres:court_case/actor"],"name_variants":["Министерство строительства и жилищно комуунального хозяйства ДНР"]},{"node_id":"org:администрация-городского-округа-мариуполь","kind":"org","canonical_name":"Администрация городского округа Мариуполь","tier":"municipal","roles":["petitioner"],"evidence":["postgres:court_case/actor"],"name_variants":["Администация.Города Мариуполя","Администрация округа Мариуполь ДНР","Администарция города Мариуполя","Администрация города Мариуполь","Администрация горлдского округа Мариуполь","Администрация города МаруиполяАдминистрация города Мариуполя Донецкой Народной Республики","администрация города Мариуполя","Администрация округа Мариуполь Донецкой Народной Республики","Администрация г.о. Мариуполь ДНР","Администрация города Мариуполя","Администрация г. Мариуполь","Администрация городскогог округа Мариуполь ДНР","Администрация городского округа Мариуполь Донецкой Народной Республики","Адмиистрация городского округа Мариуполь","Администрация городского округа Мариуполь ДНР","Администрация г. мариуполя","Администрация городского округа Мариуполя Донецкой Народной Республики","Муниципальное образование городской округ Мариуполь","Администрация грода Мариуполя","Администрация горосдкого округа Мариуполь ДНР","администрация городского округа Мариуполь","Администрация города Мариуподя","Администрация городв Мариуполя","администрация г. Мариуполя","Администрация города Мариуполя Донецкой Народной Республики","Администрация города М ариуполя","Администрацция городчского округа Мариуполь","Администрация ГО Мариуполь ДНР","Администраци г. Мариуполя","Адинистрация горолдского округа Мариуполь по ДНР","Адмминистрация городского округа Мариуполь ДНР","Администрация городского округ Маруполь","Администрация городского окрыга Мариуполь","Администрация г. Мариуполя","Администрация городского окурга Мариуполь ДНР","Администрация городского округа Мариуполя ДНР","Администрация городского округа ДНР","Администрация городского округа Маиуполь Донецкой Народной Республики","Администрация городского округа Мриуполь","Администрация городского округа Мариуполль ДНР","Администрация города Мариупоял","Администрация городского округа Мариуполь по ДНР","Админстрация города Мариуполя","Администрация Города Мариуполя","Администрация г.о. Мариуполь","Администрация г.Мариуполя","Администрация г.Мариуполя ДНР","Администрация горлдского округа Мариуполь ДНР","Администрация городского окоруга Мариуполь ДНР","Администраця города Мариуполя","Администрация городского круга Мариуполь ДНР","Администрация городского окоуга Мариуполь Донецкой Народной Республики"]},{"node_id":"person:христофоров-м-в","kind":"person","canonical_name":"Христофоров М.В.","tier":"municipal","roles":["petitioner"],"evidence":["postgres:court_case/actor"],"name_variants":["Христофоров Михаил Владимирович"]},{"node_id":"org:прокуратура-города-мариуполя","kind":"org","canonical_name":"Прокуратура города Мариуполя","tier":"dnr","roles":["petitioner"],"evidence":["postgres:court_case/actor"],"name_variants":["Прокурор города Мариуполя","Прокурор города Мариуполя старший советник юстиции Д.В. Гнездилов","Прокурор города Мариуполя Донецкой Народной Республики"]},{"node_id":"org:днр-администрация-морского-порта-г-мариуполя","kind":"org","canonical_name":"ГУП ДНР «Администрация морского порта г. Мариуполя»","tier":"dnr","roles":["petitioner"],"evidence":["postgres:court_case/actor"],"name_variants":["ГУП ДНР \"Администрация морского порта г. Мариуполя\""]},{"node_id":"org:администрация-орджоникидзевского-района-г-мариуполя","kind":"org","canonical_name":"Администрация Орджоникидзевского района г. Мариуполя","tier":"municipal","roles":["petitioner"],"evidence":["postgres:court_case/actor"],"name_variants":["Администрация Орджоникидзевского района"]},{"node_id":"person:гнездилов-д-в","kind":"person","canonical_name":"Гнездилов Д.В.","tier":"dnr","roles":["petitioner"],"org":"Прокуратура города Мариуполя","evidence":["postgres:court_case/actor"],"name_variants":["Д.В. Гнездилов"]}],"edges":[{"src":"person:кольцов-а-в","rel":"signed","dst":"instr:ownerless_decree","count":652,"date_min":"2025-07-14","date_max":"2026-02-05","source":"ownerless_decrees.jsonl","refs":["96","1859","1806","1731","1243","1107","1105"]},{"src":"person:моргун-о-в","rel":"signed","dst":"instr:ownerless_decree","count":156,"date_min":"2024-09-23","date_max":"2025-06-11","source":"ownerless_decrees.jsonl","refs":["932","825","739","623","520","298","234","703","700","421","979","748","584","151","786","706","593"]},{"src":"person:дмитриев-а-в","rel":"signed","dst":"instr:ownerless_decree","count":55,"date_min":"2024-08-16","date_max":"2025-05-14","source":"ownerless_decrees.jsonl","refs":["747","35","625","592","321","300","517","474"]},{"src":"person:краснолуцкая-т-ю","rel":"signed","dst":"instr:ownerless_decree","count":25,"date_min":"2024-12-11","date_max":"2025-03-25","source":"ownerless_decrees.jsonl","refs":["449","865","772","443","866"]},{"src":"person:перепечай-б-н","rel":"signed","dst":"instr:ownerless_decree","count":70,"date_min":"2024-08-19","date_max":"2024-10-17","source":"ownerless_decrees.jsonl","refs":["508","415","322","414","328"]},{"src":"person:матейко-в-а","rel":"signed","dst":"instr:ownerless_decree","count":8,"date_min":"2024-05-29","date_max":"2024-05-29","source":"ownerless_decrees.jsonl","refs":["163"]},{"src":"person:кольцов-а-в","rel":"signed","dst":"instr:demolition_decree","count":16,"date_min":"2025-09-16","date_max":"2026-05-20","source":"demolition_decrees.jsonl","refs":["960","212","1432"]},{"src":"person:цыба-л-в","rel":"commission_member","dst":"instr:demolition_decree","count":9,"date_min":"2024-11-18","date_max":"2026-02-26","source":"demolition_decrees.jsonl","refs":["212","1432","837","635","1707"]},{"src":"person:лысенко-м-г","rel":"commission_member","dst":"instr:demolition_decree","count":6,"date_min":"2025-09-16","date_max":"2026-02-26","source":"demolition_decrees.jsonl","refs":["212","1432","1707"]},{"src":"person:мирошниченко-я-с","rel":"commission_member","dst":"instr:demolition_decree","count":3,"date_min":"2024-11-18","date_max":"2024-12-20","source":"demolition_decrees.jsonl","refs":["837","635"]},{"src":"person:дмитриев-а-в","rel":"commission_member","dst":"instr:demolition_decree","count":2,"date_min":"2024-12-20","date_max":"2024-12-20","source":"demolition_decrees.jsonl","refs":["837"]},{"src":"person:хараджа-о-с","rel":"commission_member","dst":"instr:demolition_decree","count":2,"date_min":"2024-12-20","date_max":"2024-12-20","source":"demolition_decrees.jsonl","refs":["837"]},{"src":"person:кирьякулова-о-в","rel":"commission_member","dst":"instr:demolition_decree","count":2,"date_min":"2024-12-20","date_max":"2024-12-20","source":"demolition_decrees.jsonl","refs":["837"]},{"src":"person:клисак-н-а","rel":"commission_member","dst":"instr:demolition_decree","count":3,"date_min":"2024-11-18","date_max":"2024-12-20","source":"demolition_decrees.jsonl","refs":["837","635"]},{"src":"person:моргун-о-в","rel":"signed","dst":"instr:demolition_decree","count":1,"date_min":"2024-11-18","date_max":"2024-11-18","source":"demolition_decrees.jsonl","refs":["635"]},{"src":"person:хаджинов-д-м","rel":"commission_member","dst":"instr:demolition_decree","count":1,"date_min":"2024-11-18","date_max":"2024-11-18","source":"demolition_decrees.jsonl","refs":["635"]},{"src":"person:овсиенко-и-а","rel":"commission_member","dst":"instr:demolition_decree","count":1,"date_min":"2024-11-18","date_max":"2024-11-18","source":"demolition_decrees.jsonl","refs":["635"]},{"src":"person:пушилин-д-в","rel":"signed","dst":"instr:dnr_land_order","count":50,"date_min":"2023-09-07","date_max":"2026-06-05","source":"dnr_land_orders.jsonl","refs":["125","127","13","14","161","162","163","164","170","171","172","173","174","175","178","192","214","215","216","218","220","255","256","320","334"]},{"src":"org:порфир","rel":"received_grant","dst":"instr:dnr_land_order","count":11,"date_min":"2023-09-07","date_max":"2026-05-14","source":"dnr_land_orders.jsonl","refs":["125","162","163","164","390","391","392","393","394","289"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:порфир","count":11,"date_min":"2023-09-07","date_max":"2026-05-14","source":"dnr_land_orders.jsonl","refs":["125","162","163","164","390","391","392","393","394","289"]},{"src":"org:сгм-монтаж","rel":"received_grant","dst":"instr:dnr_land_order","count":1,"date_min":"2026-04-24","date_max":"2026-04-24","source":"dnr_land_orders.jsonl","refs":["127"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:сгм-монтаж","count":1,"date_min":"2026-04-24","date_max":"2026-04-24","source":"dnr_land_orders.jsonl","refs":["127"]},{"src":"org:олимпстрой-нр","rel":"received_grant","dst":"instr:dnr_land_order","count":2,"date_min":"2025-01-20","date_max":"2025-01-20","source":"dnr_land_orders.jsonl","refs":["13","14"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:олимпстрой-нр","count":2,"date_min":"2025-01-20","date_max":"2025-01-20","source":"dnr_land_orders.jsonl","refs":["13","14"]},{"src":"org:эверест-домостроение","rel":"received_grant","dst":"instr:dnr_land_order","count":2,"date_min":"2026-05-14","date_max":"2026-06-05","source":"dnr_land_orders.jsonl","refs":["161","192"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:эверест-домостроение","count":2,"date_min":"2026-05-14","date_max":"2026-06-05","source":"dnr_land_orders.jsonl","refs":["161","192"]},{"src":"org:строительное-управление-2007","rel":"received_grant","dst":"instr:dnr_land_order","count":6,"date_min":"2023-09-07","date_max":"2023-09-07","source":"dnr_land_orders.jsonl","refs":["170","171","172","173","174","290"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:строительное-управление-2007","count":6,"date_min":"2023-09-07","date_max":"2023-09-07","source":"dnr_land_orders.jsonl","refs":["170","171","172","173","174","290"]},{"src":"org:мирастрой-3","rel":"received_grant","dst":"instr:dnr_land_order","count":1,"date_min":"2024-04-19","date_max":"2024-04-19","source":"dnr_land_orders.jsonl","refs":["175"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:мирастрой-3","count":1,"date_min":"2024-04-19","date_max":"2024-04-19","source":"dnr_land_orders.jsonl","refs":["175"]},{"src":"org:мирастрой-4","rel":"received_grant","dst":"instr:dnr_land_order","count":1,"date_min":"2024-04-19","date_max":"2024-04-19","source":"dnr_land_orders.jsonl","refs":["178"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:мирастрой-4","count":1,"date_min":"2024-04-19","date_max":"2024-04-19","source":"dnr_land_orders.jsonl","refs":["178"]},{"src":"org:новое-время-3","rel":"received_grant","dst":"instr:dnr_land_order","count":1,"date_min":"2026-05-25","date_max":"2026-05-25","source":"dnr_land_orders.jsonl","refs":["178"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:новое-время-3","count":1,"date_min":"2026-05-25","date_max":"2026-05-25","source":"dnr_land_orders.jsonl","refs":["178"]},{"src":"org:корпорация-сму-5","rel":"received_grant","dst":"instr:dnr_land_order","count":1,"date_min":null,"date_max":null,"source":"dnr_land_orders.jsonl","refs":["178"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:корпорация-сму-5","count":1,"date_min":null,"date_max":null,"source":"dnr_land_orders.jsonl","refs":["178"]},{"src":"org:эводом-5","rel":"received_grant","dst":"instr:dnr_land_order","count":9,"date_min":"2025-01-20","date_max":"2025-06-24","source":"dnr_land_orders.jsonl","refs":["214","215","216","255","256","395","396","397","7"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:эводом-5","count":9,"date_min":"2025-01-20","date_max":"2025-06-24","source":"dnr_land_orders.jsonl","refs":["214","215","216","255","256","395","396","397","7"]},{"src":"org:солнечная","rel":"received_grant","dst":"instr:dnr_land_order","count":2,"date_min":null,"date_max":null,"source":"dnr_land_orders.jsonl","refs":["218","220"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:солнечная","count":2,"date_min":null,"date_max":null,"source":"dnr_land_orders.jsonl","refs":["218","220"]},{"src":"org:строительное-управление-2007-инвест","rel":"received_grant","dst":"instr:dnr_land_order","count":2,"date_min":"2025-09-16","date_max":"2025-10-01","source":"dnr_land_orders.jsonl","refs":["320","334"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:строительное-управление-2007-инвест","count":2,"date_min":"2025-09-16","date_max":"2025-10-01","source":"dnr_land_orders.jsonl","refs":["320","334"]},{"src":"org:региональная-строительная-компания","rel":"received_grant","dst":"instr:dnr_land_order","count":2,"date_min":"2024-09-02","date_max":"2024-09-02","source":"dnr_land_orders.jsonl","refs":["339","340"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:региональная-строительная-компания","count":2,"date_min":"2024-09-02","date_max":"2024-09-02","source":"dnr_land_orders.jsonl","refs":["339","340"]},{"src":"org:сириус-билд","rel":"received_grant","dst":"instr:dnr_land_order","count":1,"date_min":"2024-11-18","date_max":"2024-11-18","source":"dnr_land_orders.jsonl","refs":["414"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:сириус-билд","count":1,"date_min":"2024-11-18","date_max":"2024-11-18","source":"dnr_land_orders.jsonl","refs":["414"]},{"src":"org:антарес","rel":"received_grant","dst":"instr:dnr_land_order","count":1,"date_min":"2024-11-18","date_max":"2024-11-18","source":"dnr_land_orders.jsonl","refs":["415"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:антарес","count":1,"date_min":"2024-11-18","date_max":"2024-11-18","source":"dnr_land_orders.jsonl","refs":["415"]},{"src":"org:восход","rel":"received_grant","dst":"instr:dnr_land_order","count":2,"date_min":"2025-11-22","date_max":"2025-11-22","source":"dnr_land_orders.jsonl","refs":["419","420"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:восход","count":2,"date_min":"2025-11-22","date_max":"2025-11-22","source":"dnr_land_orders.jsonl","refs":["419","420"]},{"src":"org:осс","rel":"received_grant","dst":"instr:dnr_land_order","count":1,"date_min":"2024-12-18","date_max":"2024-12-18","source":"dnr_land_orders.jsonl","refs":["448"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:осс","count":1,"date_min":"2024-12-18","date_max":"2024-12-18","source":"dnr_land_orders.jsonl","refs":["448"]},{"src":"org:ркс-девелопмент","rel":"received_grant","dst":"instr:dnr_land_order","count":1,"date_min":"2023-09-07","date_max":"2023-09-07","source":"dnr_land_orders.jsonl","refs":["291"]},{"src":"person:пушилин-д-в","rel":"granted_land_to","dst":"org:ркс-девелопмент","count":1,"date_min":"2023-09-07","date_max":"2023-09-07","source":"dnr_land_orders.jsonl","refs":["291"]},{"src":"org:гк-трансстройинвест","rel":"received_contract","dst":"instr:reconstruction","count":217,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":["бульвар Богдана Хмельницкого , 12","бульвар Богдана Хмельницкого , 14","бульвар Богдана Хмельницкого , 16","бульвар Богдана Хмельницкого , 17/91","бульвар Богдана Хмельницкого , 18","бульвар Богдана Хмельницкого , 20","бульвар Богдана Хмельницкого , 20А","бульвар Богдана Хмельницкого , 23А","бульвар Богдана Хмельницкого , 25","бульвар Богдана Хмельницкого , 27","бульвар Богдана Хмельницкого , 29","бульвар Богдана Хмельницкого , 31","бульвар Богдана Хмельницкого , 33","бульвар Богдана Хмельницкого , 35","бульвар Богдана Хмельницкого , 37","бульвар Богдана Хмельницкого , 38","бульвар Богдана Хмельницкого , 39","переулок Трамвайный , 10","переулок Трамвайный , 35","проспект Ленина (Мира) , 102","проспект Ленина (Мира) , 104","проспект Ленина (Мира) , 106","проспект Ленина (Мира) , 107","проспект Ленина (Мира) , 108","проспект Ленина (Мира) , 110"]},{"src":"org:единый-заказчик","rel":"oversees","dst":"org:гк-трансстройинвест","count":217,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":[]},{"src":"org:гк-екс","rel":"received_contract","dst":"instr:reconstruction","count":251,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":["бульвар Шевченко , 226","бульвар Шевченко , 228","бульвар Шевченко , 234/147","бульвар Шевченко , 238","бульвар Шевченко , 240","бульвар Шевченко , 242","бульвар Шевченко , 244","бульвар Шевченко , 248","бульвар Шевченко , 250","бульвар Шевченко , 252","бульвар Шевченко , 258","бульвар Шевченко , 260","бульвар Шевченко , 262","бульвар Шевченко , 264","бульвар Шевченко , 266","бульвар Шевченко , 268","бульвар Шевченко , 270","бульвар Шевченко , 272","бульвар Шевченко , 274","бульвар Шевченко , 276","бульвар Шевченко , 287","бульвар Шевченко , 289","бульвар Шевченко , 291","бульвар Шевченко , 293","бульвар Шевченко , 295"]},{"src":"org:единый-заказчик","rel":"oversees","dst":"org:гк-екс","count":251,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":[]},{"src":"org:крост","rel":"received_contract","dst":"instr:reconstruction","count":309,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":["бульвар Шевченко , 62","бульвар Шевченко , 64","бульвар Шевченко , 64А","бульвар Шевченко , 68","бульвар Шевченко , 70","бульвар Шевченко , 71","бульвар Шевченко , 72","бульвар Шевченко , 73","бульвар Шевченко , 74","бульвар Шевченко , 76","бульвар Шевченко , 77","бульвар Шевченко , 79","бульвар Шевченко , 81","бульвар Шевченко , 83","бульвар Шевченко , 85","бульвар Шевченко , 87","бульвар Шевченко , 91","бульвар Шевченко , 93","переулок Нахимова , 3","переулок Нахимова , 5","проспект Ленина (Мира) , 10/20","проспект Ленина (Мира) , 101","проспект Ленина (Мира) , 103","проспект Ленина (Мира) , 105","проспект Ленина (Мира) , 11"]},{"src":"org:единый-заказчик","rel":"oversees","dst":"org:крост","count":309,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":[]},{"src":"org:московская-область","rel":"received_contract","dst":"instr:reconstruction","count":124,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":["проспект Маршала Жукова , 78","проспект Маршала Жукова , 80","проспект Маршала Жукова , 82","улица Киевская , 70","улица Киевская , 76","улица Киевская , 94","улица Олимпийская , 163","улица Олимпийская , 175","улица Олимпийская , 181","улица Олимпийская , 185","улица Олимпийская , 187","улица Олимпийская , 189","улица Олимпийская , 65","улица Олимпийская , 73","улица 9 Мая , 18","улица Киевская , 13","улица Киевская , 11-1","улица Киевская , 7","улица Киевская , 11-3","улица Киевская , 3-1","улица Киевская , 5","улица Пейзажная , 40-1","улица Пейзажная , 40-2","улица Киевская , 3-3","улица Киевская , 33"]},{"src":"org:крокус-групп","rel":"received_contract","dst":"instr:reconstruction","count":114,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":["улица Февральская , 42","улица 130 Таганрогской дивизии , 10","улица 130 Таганрогской дивизии , 106","улица 130 Таганрогской дивизии , 108","улица Волгоградская , 8","бульвар Комсомольский , 46","бульвар Комсомольский , 48","бульвар Комсомольский , 50","бульвар Комсомольский , 52","бульвар Комсомольский , 54","бульвар Комсомольский , 56","бульвар Комсомольский , 58","бульвар Комсомольский , 60","бульвар Комсомольский , 62","улица Межевая , 17","улица Межевая , 19","улица 130 Таганрогской дивизии , 108-110","улица 130 Таганрогской дивизии , 112","переулок Каховского , 84","переулок Полетаева , 120","переулок Ровенский , 15","переулок Ровенский , 17","переулок Ровенский , 19","проспект Ленинградский , 37","проспект Ленинградский , 39"]},{"src":"org:единый-заказчик","rel":"oversees","dst":"org:крокус-групп","count":114,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":[]},{"src":"org:тульская-область","rel":"received_contract","dst":"instr:reconstruction","count":90,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":["улица Азовстальская , 43-6","улица Азовстальская , 45","улица Азовстальская , 51","улица Азовстальская , 57","улица Азовстальская , 61","улица Воинов-Освободителей , 14","улица Воинов-Освободителей , 12","улица Воинов-Освободителей , 10","улица Воинов-Освободителей , 66","улица Азовстальская , 158а","улица Азовстальская , 158б","улица Азовстальская , 158в","улица Азовстальская , 160","улица Азовстальская , 162","улица Азовстальская , 164","улица Азовстальская , 166","улица Азовстальская , 168","улица Азовстальская , 170","улица Московская , 64","улица Московская , 61","улица Московская , 63","улица Азовстальская , 101","улица Азовстальская , 103","улица Азовстальская , 99","улица Азовстальская , 97"]},{"src":"org:ук-новый-капитал","rel":"received_contract","dst":"instr:reconstruction","count":212,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":["25 квартал , 1","25 квартал , 2","25 квартал , 9","26 квартал , 11","26 квартал , 13а","26 квартал , 3","26 квартал , 4","26 квартал , 6","26 квартал , 8","26 квартал , 9","27 квартал , 11","27 квартал , 1-1а","27 квартал , 12-12а","27 квартал , 14","27 квартал , 15","27 квартал , 15а","27 квартал , 16","27 квартал , 18-18а","27 квартал , 19","27 квартал , 2","27 квартал , 20","27 квартал , 21а","27 квартал , 32","27 квартал , 3-3а","27 квартал , 4-4а"]},{"src":"org:единый-заказчик","rel":"oversees","dst":"org:ук-новый-капитал","count":212,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":[]},{"src":"org:пск-строймонолит","rel":"received_contract","dst":"instr:reconstruction","count":151,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":["городок Охраны , 1","городок Охраны , 2","городок Охраны , 3","городок Охраны , 4","городок Охраны , 5","городок Охраны , 6","переулок Благовещенский , 10","переулок Благовещенский , 8","проспект Ильича , 11","проспект Ильича , 4","проспект Ильича , 13","проспект Ильича , 135","проспект Ильича , 137","проспект Ильича , 138","проспект Ильича , 140","проспект Ильича , 5","проспект Ильича , 7","проспект Ильича , 9","проспект Металлургов , 135","проспект Металлургов , 137","проспект Металлургов , 139","проспект Металлургов , 141","проспект Металлургов , 143","проспект Металлургов , 145","проспект Металлургов , 147"]},{"src":"org:единый-заказчик","rel":"oversees","dst":"org:пск-строймонолит","count":151,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":[]},{"src":"org:спецснабтранс","rel":"received_contract","dst":"instr:reconstruction","count":54,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":["переулок Ермака , 31","улица Варшавская , 23","улица Героическая , 27","улица Героическая , 29","улица Героическая , 31","улица Курчатова , 37","улица Курчатова , 39","улица Курчатова , 41","улица Курчатова , 43","улица Курчатова , 51","улица Курчатова , 53","улица Курчатова , 55","улица Курчатова , 57","улица Курчатова , 59","улица Курчатова , 61","улица Курчатова , 63","улица Мамина-Сибиряка , 35","улица Мамина-Сибиряка , 36","улица Мамина-Сибиряка , 37","улица Мамина-Сибиряка , 39","улица Мамина-Сибиряка , 40","улица Мамина-Сибиряка , 42","улица Мамина-Сибиряка , 43","улица Мамина-Сибиряка , 44","улица Мамина-Сибиряка , 45"]},{"src":"org:единый-заказчик","rel":"oversees","dst":"org:спецснабтранс","count":54,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":[]},{"src":"org:московский-политех","rel":"received_contract","dst":"instr:reconstruction","count":120,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":["жилмасив Азовский , 4","жилмасив Азовский , 9","квартал Азовье , 1","квартал Азовье , 10","квартал Азовье , 2","квартал Азовье , 5","квартал Азовье , 6","проспект Лунина , 10","проспект Лунина , 11","проспект Лунина , 11а","проспект Лунина , 11б","проспект Лунина , 11в","проспект Лунина , 12","проспект Лунина , 13","проспект Лунина , 13а","проспект Лунина , 13б","проспект Лунина , 13в","проспект Лунина , 14","проспект Лунина , 15","проспект Лунина , 15а","проспект Лунина , 16","проспект Лунина , 17","проспект Лунина , 18","проспект Лунина , 21","проспект Лунина , 23"]},{"src":"org:единый-заказчик","rel":"oversees","dst":"org:московский-политех","count":120,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":[]},{"src":"org:монотек-строй","rel":"received_contract","dst":"instr:reconstruction","count":187,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":["бульвар Богдана Хмельницкого , 2","бульвар Богдана Хмельницкого , 6","бульвар Богдана Хмельницкого , 8","переулок Днепропетровский , 11","переулок Днепропетровский , 13","переулок Днепропетровский , 15","переулок Днепропетровский , 3","переулок Днепропетровский , 5","переулок Черноморский , 3","переулок Черноморский , 5","проспект Нахимова , 100","проспект Нахимова , 102","проспект Нахимова , 104","проспект Нахимова , 106","проспект Нахимова , 106а","проспект Нахимова , 108","проспект Нахимова , 112","проспект Нахимова , 114","проспект Нахимова , 114а","проспект Нахимова , 116","проспект Нахимова , 118","проспект Нахимова , 120","проспект Нахимова , 120а","проспект Нахимова , 122","проспект Нахимова , 124"]},{"src":"org:единый-заказчик","rel":"oversees","dst":"org:монотек-строй","count":187,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":[]},{"src":"org:интеко","rel":"received_contract","dst":"instr:reconstruction","count":187,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":["бульвар Богдана Хмельницкого , 2","бульвар Богдана Хмельницкого , 6","бульвар Богдана Хмельницкого , 8","переулок Днепропетровский , 11","переулок Днепропетровский , 13","переулок Днепропетровский , 15","переулок Днепропетровский , 3","переулок Днепропетровский , 5","переулок Черноморский , 3","переулок Черноморский , 5","проспект Нахимова , 100","проспект Нахимова , 102","проспект Нахимова , 104","проспект Нахимова , 106","проспект Нахимова , 106а","проспект Нахимова , 108","проспект Нахимова , 112","проспект Нахимова , 114","проспект Нахимова , 114а","проспект Нахимова , 116","проспект Нахимова , 118","проспект Нахимова , 120","проспект Нахимова , 120а","проспект Нахимова , 122","проспект Нахимова , 124"]},{"src":"org:единый-заказчик","rel":"oversees","dst":"org:интеко","count":187,"date_min":null,"date_max":null,"source":"damage_assessment.jsonl","refs":[]},{"src":"org:комитет-по-тарифам-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":4,"date_min":"2025-06-18","date_max":"2026-05-25","source":"pravo_region80_relevant.jsonl","refs":["Постановление 7/1","Постановление 5/8","Постановление 17/3","Постановление 5/1"]},{"src":"org:правительство-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":219,"date_min":"2023-12-04","date_max":"2026-06-04","source":"pravo_region80_relevant.jsonl","refs":["Постановление 48-4","Постановление 48-3","Постановление 48-2","Постановление 45-1","Постановление 43-3","Постановление 43-2","Постановление 42-4","Постановление 41-1","Постановление 39-4","Постановление 39-2","Постановление 37-3","Постановление 35-6","Постановление 35-5","Постановление 32-5","Постановление 32-3","Постановление 29-4","Постановление 29-3","Постановление 26-9","Постановление 26-7","Постановление 26-10","Постановление 22-2","Постановление 20-3","Постановление 16-6","Постановление 15-1","Постановление 13-2"]},{"src":"org:глава-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":82,"date_min":"2023-12-08","date_max":"2026-06-02","source":"pravo_region80_relevant.jsonl","refs":["Указ 301","Указ 290","Указ 246","Указ 184","Указ 135","Указ 61","Указ 39","Указ 17","Указ 1022","Указ 1021","Указ 970","Указ 852","Указ 851","Указ 844","Указ 828","Указ 750","Указ 696","Указ 693","Указ 653","Указ 651","Указ 635","Указ 626","Указ 614","Указ 602","Указ 600"]},{"src":"org:министерство-строительства-архитектуры-и-жилищно-коммунального-хозяйства-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":3,"date_min":"2025-07-10","date_max":"2026-03-13","source":"pravo_region80_relevant.jsonl","refs":["Приказ 72-од","Приказ 359-од","Приказ 146-од"]},{"src":"org:донецкая-народная-республика","rel":"issued","dst":"instr:dnr_normative_act","count":48,"date_min":"2023-11-30","date_max":"2026-05-15","source":"pravo_region80_relevant.jsonl","refs":["Закон 282-РЗ","Закон 280-РЗ","Закон 279-РЗ","Закон 275-РЗ","Закон 273-РЗ","Закон 272-РЗ","Закон 269-РЗ","Закон 266-РЗ","Закон 263-РЗ","Закон 261-РЗ","Закон 255-РЗ","Закон 253-РЗ","Закон 243-РЗ","Закон 240-РЗ","Закон 222-РЗ","Закон 221-РЗ","Закон 207-РЗ","Закон 204-РЗ","Закон 203-РЗ","Закон 191-РЗ","Закон 187-РЗ","Закон 171-РЗ","Закон 170-РЗ","Закон 168-РЗ","Закон 161-РЗ"]},{"src":"org:министерство-спорта-и-туризма-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":1,"date_min":"2026-02-13","date_max":"2026-02-13","source":"pravo_region80_relevant.jsonl","refs":["Приказ 01-09/49"]},{"src":"org:министерство-имущественных-и-земельных-отношений-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":6,"date_min":"2025-03-28","date_max":"2025-12-30","source":"pravo_region80_relevant.jsonl","refs":["Приказ 1221","Приказ 1112","Приказ 217","Приказ 216","Приказ 339","Приказ 215"]},{"src":"org:министерство-культуры-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":2,"date_min":"2025-07-09","date_max":"2025-12-24","source":"pravo_region80_relevant.jsonl","refs":["Приказ 285-ОД","Приказ 156-ОД"]},{"src":"org:министерство-природных-ресурсов-и-экологии-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":3,"date_min":"2025-05-26","date_max":"2025-10-14","source":"pravo_region80_relevant.jsonl","refs":["Приказ 182","Приказ 181","Приказ 96"]},{"src":"org:министерство-образования-и-науки-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":4,"date_min":"2024-06-26","date_max":"2025-09-12","source":"pravo_region80_relevant.jsonl","refs":["Приказ 10-НП","Приказ 3-НП","Приказ 16-НП"]},{"src":"org:министерство-промышленности-и-торговли-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":3,"date_min":"2024-04-04","date_max":"2025-07-14","source":"pravo_region80_relevant.jsonl","refs":["Приказ 107","Приказ 53-ОП","Приказ 33-С"]},{"src":"org:республиканская-служба-по-тарифам-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":5,"date_min":"2023-12-08","date_max":"2024-11-29","source":"pravo_region80_relevant.jsonl","refs":["Постановление 24/5","Постановление 24/2","Постановление 2/1","Постановление 35/2","Постановление 32/3"]},{"src":"org:министерство-труда-и-социальной-политики-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":6,"date_min":"2023-12-11","date_max":"2024-10-03","source":"pravo_region80_relevant.jsonl","refs":["Приказ 133/Д","Приказ 114/Д","Приказ 111/Д","Приказ 47/Д","Приказ 125/Д","Приказ 132/Д"]},{"src":"org:главное-управления-геологии-и-геоэкологии-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":3,"date_min":"2024-04-15","date_max":"2024-04-22","source":"pravo_region80_relevant.jsonl","refs":["Приказ 37","Приказ 35","Приказ 33"]},{"src":"org:фонд-государственного-имущества-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":4,"date_min":"2023-12-08","date_max":"2024-02-22","source":"pravo_region80_relevant.jsonl","refs":["Приказ 47","Приказ 207","Приказ 2295","Приказ 2294"]},{"src":"org:государственный-комитет-по-земельным-ресурсам-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":1,"date_min":"2024-02-20","date_max":"2024-02-20","source":"pravo_region80_relevant.jsonl","refs":["Приказ 80"]},{"src":"org:министерство-строительства-и-жилищно-коммунального-хозяйства-донецкой-народной-республики","rel":"issued","dst":"instr:dnr_normative_act","count":1,"date_min":"2024-02-07","date_max":"2024-02-07","source":"pravo_region80_relevant.jsonl","refs":["Приказ 11-од"]},{"src":"person:харламова-т-с","rel":"directs","dst":"org:сгм-монтаж","count":1,"date_min":null,"date_max":null,"source":"egrul_inn_lookups.jsonl","refs":["9310018029"]},{"src":"person:василенко-и-и","rel":"directs","dst":"org:мирастрой-3","count":1,"date_min":null,"date_max":null,"source":"egrul_inn_lookups.jsonl","refs":["9303036524"]},{"src":"person:митин-с-в","rel":"directs","dst":"org:новое-время-3","count":1,"date_min":null,"date_max":null,"source":"egrul_inn_lookups.jsonl","refs":["9309028294"]},{"src":"person:сарибекян-а-в","rel":"directs","dst":"org:олимпстрой-нр","count":1,"date_min":null,"date_max":null,"source":"egrul_inn_lookups.jsonl","refs":["9309027678"]},{"src":"person:попченко-в-г","rel":"directs","dst":"org:эверест-домостроение","count":1,"date_min":null,"date_max":null,"source":"egrul_inn_lookups.jsonl","refs":["9303042743"]},{"src":"person:крючков-а-м","rel":"directs","dst":"org:су-2007-инвест","count":1,"date_min":null,"date_max":null,"source":"egrul_inn_lookups.jsonl","refs":["9310015807"]},{"src":"person:лопухов-к-к","rel":"directs","dst":"org:ркс-девелопмент","count":1,"date_min":null,"date_max":null,"source":"egrul_inn_lookups.jsonl","refs":["9310007980"]},{"src":"org:военно-строительная-компания","rel":"received_contract","dst":"org:олимпситистрой","count":1,"date_min":null,"date_max":null,"source":"open_source_investigations.jsonl","refs":["main contractor relationship, ~47bn RUB 2022 revenue"]},{"src":"org:олимпситистрой","rel":"subcontracted_to","dst":"org:оборонспецстрой","count":1,"date_min":null,"date_max":null,"source":"open_source_investigations.jsonl","refs":["ЖК Невский, Mariupol, developer-of-record"]},{"src":"person:хавронин-д-а","rel":"founder_of","dst":"org:олимпситистрой","count":1,"date_min":null,"date_max":null,"source":"open_source_investigations.jsonl","refs":[]},{"src":"person:фомин-а-г","rel":"founder_of","dst":"org:олимпситистрой","count":1,"date_min":null,"date_max":null,"source":"open_source_investigations.jsonl","refs":[]},{"src":"person:иванов-т-в","rel":"patron_of","dst":"org:военно-строительная-компания","count":1,"date_min":null,"date_max":null,"source":"open_source_investigations.jsonl","refs":["lobbied VSK into existence, 2020"]},{"src":"person:иванов-т-в","rel":"benefited_from","dst":"org:оборонспецстрой","count":1,"date_min":null,"date_max":null,"source":"open_source_investigations.jsonl","refs":["marble for mansion; Tver land adjacent to family estate"]},{"src":"person:сазонова-ю-ю","rel":"ruled_in","dst":"instr:court_proceedings","count":118,"date_min":"2024-07-21","date_max":"2026-01-15","source":"postgres:court_case/actor","refs":[]},{"src":"person:маркова-е-в","rel":"ruled_in","dst":"instr:court_proceedings","count":4,"date_min":"2025-12-09","date_max":"2026-03-18","source":"postgres:court_case/actor","refs":[]},{"src":"person:гревцова-в-а","rel":"ruled_in","dst":"instr:court_proceedings","count":188,"date_min":"2024-08-12","date_max":"2026-02-09","source":"postgres:court_case/actor","refs":[]},{"src":"person:нидзиева-н-н","rel":"ruled_in","dst":"instr:court_proceedings","count":128,"date_min":"2024-08-28","date_max":"2025-12-26","source":"postgres:court_case/actor","refs":[]},{"src":"person:леонов-а-ю","rel":"ruled_in","dst":"instr:court_proceedings","count":127,"date_min":"2024-08-07","date_max":"2025-12-17","source":"postgres:court_case/actor","refs":[]},{"src":"person:кенжегарина-д-м","rel":"ruled_in","dst":"instr:court_proceedings","count":74,"date_min":"2025-06-26","date_max":"2026-04-27","source":"postgres:court_case/actor","refs":[]},{"src":"person:ремпе-м-в","rel":"ruled_in","dst":"instr:court_proceedings","count":9,"date_min":"2024-09-23","date_max":"2025-01-29","source":"postgres:court_case/actor","refs":[]},{"src":"person:таубаева-а-у","rel":"ruled_in","dst":"instr:court_proceedings","count":10,"date_min":"2024-08-26","date_max":"2024-09-06","source":"postgres:court_case/actor","refs":[]},{"src":"person:струнов-н-и","rel":"ruled_in","dst":"instr:court_proceedings","count":143,"date_min":"2024-09-06","date_max":"2026-05-22","source":"postgres:court_case/actor","refs":[]},{"src":"person:митерев-э-е","rel":"ruled_in","dst":"instr:court_proceedings","count":57,"date_min":"2024-09-13","date_max":"2025-11-20","source":"postgres:court_case/actor","refs":[]},{"src":"person:мяконькая-т-а","rel":"ruled_in","dst":"instr:court_proceedings","count":201,"date_min":"2024-09-12","date_max":"2026-02-17","source":"postgres:court_case/actor","refs":[]},{"src":"person:кралинина-н-г","rel":"ruled_in","dst":"instr:court_proceedings","count":173,"date_min":"2024-07-30","date_max":"2025-12-25","source":"postgres:court_case/actor","refs":[]},{"src":"person:романов-д-с","rel":"ruled_in","dst":"instr:court_proceedings","count":288,"date_min":"2024-08-21","date_max":"2026-01-15","source":"postgres:court_case/actor","refs":[]},{"src":"person:дулькина-н-в","rel":"ruled_in","dst":"instr:court_proceedings","count":66,"date_min":"2025-07-31","date_max":"2026-02-05","source":"postgres:court_case/actor","refs":[]},{"src":"person:сахапова-р-р","rel":"ruled_in","dst":"instr:court_proceedings","count":83,"date_min":"2024-09-06","date_max":"2025-12-09","source":"postgres:court_case/actor","refs":[]},{"src":"person:бойко-в-о","rel":"ruled_in","dst":"instr:court_proceedings","count":85,"date_min":"2024-11-07","date_max":"2026-02-11","source":"postgres:court_case/actor","refs":[]},{"src":"person:ахтямова-э-с","rel":"ruled_in","dst":"instr:court_proceedings","count":90,"date_min":"2024-09-23","date_max":"2025-12-08","source":"postgres:court_case/actor","refs":[]},{"src":"person:степанова-е-в","rel":"ruled_in","dst":"instr:court_proceedings","count":59,"date_min":"2025-01-14","date_max":"2025-12-19","source":"postgres:court_case/actor","refs":[]},{"src":"person:логвинов-о-в","rel":"ruled_in","dst":"instr:court_proceedings","count":80,"date_min":"2025-01-13","date_max":"2025-12-11","source":"postgres:court_case/actor","refs":[]},{"src":"person:белоусов-п-в","rel":"ruled_in","dst":"instr:court_proceedings","count":162,"date_min":"2024-08-07","date_max":"2026-03-20","source":"postgres:court_case/actor","refs":[]},{"src":"person:тлеужанова-б-е","rel":"ruled_in","dst":"instr:court_proceedings","count":146,"date_min":"2024-09-30","date_max":"2026-02-09","source":"postgres:court_case/actor","refs":[]},{"src":"person:гузаирова-э-и","rel":"ruled_in","dst":"instr:court_proceedings","count":2,"date_min":"2026-03-05","date_max":"2026-04-15","source":"postgres:court_case/actor","refs":[]},{"src":"person:павленко-д-к","rel":"ruled_in","dst":"instr:court_proceedings","count":93,"date_min":"2024-09-19","date_max":"2026-03-02","source":"postgres:court_case/actor","refs":[]},{"src":"person:резниченко-в-а","rel":"ruled_in","dst":"instr:court_proceedings","count":138,"date_min":"2024-07-31","date_max":"2026-04-27","source":"postgres:court_case/actor","refs":[]},{"src":"person:климова-с-ю","rel":"ruled_in","dst":"instr:court_proceedings","count":17,"date_min":"2024-09-04","date_max":"2025-04-29","source":"postgres:court_case/actor","refs":[]},{"src":"person:головченко-ю-н","rel":"ruled_in","dst":"instr:court_proceedings","count":46,"date_min":"2025-02-14","date_max":"2025-12-19","source":"postgres:court_case/actor","refs":[]},{"src":"person:гаврилюк-е-а","rel":"ruled_in","dst":"instr:court_proceedings","count":4,"date_min":"2025-02-21","date_max":"2025-02-21","source":"postgres:court_case/actor","refs":[]},{"src":"person:мартынов-а-а","rel":"ruled_in","dst":"instr:court_proceedings","count":66,"date_min":"2025-01-24","date_max":"2025-12-19","source":"postgres:court_case/actor","refs":[]},{"src":"org:министерство-строительства-и-жкх-донецкой-народной-республики","rel":"petitioned","dst":"instr:court_proceedings","count":1,"date_min":null,"date_max":null,"source":"postgres:court_case/actor","refs":[]},{"src":"org:администрация-городского-округа-мариуполь","rel":"petitioned","dst":"instr:court_proceedings","count":53,"date_min":null,"date_max":null,"source":"postgres:court_case/actor","refs":[]},{"src":"org:министерство-имущественных-и-земельных-отношений-донецкой-народной-республики","rel":"petitioned","dst":"instr:court_proceedings","count":4,"date_min":null,"date_max":null,"source":"postgres:court_case/actor","refs":[]},{"src":"person:христофоров-м-в","rel":"petitioned","dst":"instr:court_proceedings","count":1,"date_min":null,"date_max":null,"source":"postgres:court_case/actor","refs":[]},{"src":"org:прокуратура-города-мариуполя","rel":"petitioned","dst":"instr:court_proceedings","count":3,"date_min":null,"date_max":null,"source":"postgres:court_case/actor","refs":[]},{"src":"org:днр-администрация-морского-порта-г-мариуполя","rel":"petitioned","dst":"instr:court_proceedings","count":1,"date_min":null,"date_max":null,"source":"postgres:court_case/actor","refs":[]},{"src":"org:администрация-орджоникидзевского-района-г-мариуполя","rel":"petitioned","dst":"instr:court_proceedings","count":1,"date_min":null,"date_max":null,"source":"postgres:court_case/actor","refs":[]},{"src":"person:гнездилов-д-в","rel":"petitioned","dst":"instr:court_proceedings","count":1,"date_min":null,"date_max":null,"source":"postgres:court_case/actor","refs":[]},{"src":"org:фонд-государственного-имущества-донецкой-народной-республики","rel":"petitioned","dst":"instr:court_proceedings","count":4,"date_min":null,"date_max":null,"source":"postgres:court_case/actor","refs":[]}]};

const TIER_META = {
  federal:    { label: "Federal RF",          short: "Federal",    color: "#5b8fc9", order: 0 },
  dnr:        { label: "DNR republic",         short: "DNR",        color: "#9b7bc9", order: 1 },
  municipal:  { label: "Mariupol municipal",   short: "Municipal",  color: "#d98a3d", order: 2 },
  judicial:   { label: "Judicial",             short: "Judicial",   color: "#cd4f43", order: 3 },
  commercial: { label: "Commercial",           short: "Commercial", color: "#5aa86b", order: 4 },
  pipeline:   { label: "Instrument bridge",    short: "Instrument", color: "#8a929e", order: 5 },
};
const TIER_ORDER = ["federal", "dnr", "municipal", "judicial", "commercial"];

const REL_LABEL = {
  signed: "signed", issued: "issued", ruled_in: "ruled in", petitioned: "petitioned",
  granted_land_to: "granted land to", received_grant: "received grant",
  received_contract: "received contract", oversees: "oversees",
  commission_member: "commission member", directs: "directs",
  subcontracted_to: "subcontracted to", founder_of: "founder of",
  patron_of: "patron of", benefited_from: "benefited from",
};

// Style guide rule 1: render Cyrillic person/org names English-first via
// transliteration, original on demand. This exhibit is graph/data-driven
// (every label sits inside an onClick node or row), so per the guide's own
// "inside a clickable element -> title tooltip" rule, a native `title`
// attribute carries the Cyrillic original rather than the `.xlit` click-
// popup component used in the prose exhibits.
const _XLIT_MAP = {
  а:"a", б:"b", в:"v", г:"g", д:"d", е:"e", ё:"yo", ж:"zh", з:"z", и:"i",
  й:"y", к:"k", л:"l", м:"m", н:"n", о:"o", п:"p", р:"r", с:"s", т:"t",
  у:"u", ф:"f", х:"kh", ц:"ts", ч:"ch", ш:"sh", щ:"shch", ъ:"", ы:"y",
  ь:"", э:"e", ю:"yu", я:"ya", "«":"“", "»":"”",
};
function translit(s) {
  if (!s) return s;
  let out = "";
  for (const ch of s) {
    const lower = ch.toLowerCase();
    const mapped = _XLIT_MAP[lower];
    if (mapped === undefined) { out += ch; continue; }
    out += (ch !== lower && mapped) ? mapped[0].toUpperCase() + mapped.slice(1) : mapped;
  }
  return out;
}
function enName(name) {
  return name && /[А-Яа-яЁё]/.test(name) ? translit(name) : name;
}
// Researched full names (given name + patronymic), per STYLE_GUIDE.md rule 5 —
// only the figures significant enough to warrant the research effort. Every
// other node falls back to the mechanical enName()/canonical_name pair above.
const DISPLAY_NAME_OVERRIDES = {
  "person:пушилин-д-в":   { en: "Denis Pushilin",     fio: "Пушилин Денис Владимирович" },
  "person:моргун-о-в":    { en: "Oleg Morgun",        fio: "Моргун Олег Валериевич" },
  "person:кольцов-а-в":   { en: "Anton Koltsov",      fio: "Кольцов Антон Викторович" },
  "person:романов-д-с":   { en: "Dmitry Romanov",     fio: "Романов Дмитрий Сергеевич" },
  "person:гнездилов-д-в": { en: "Denis Gnezdilov",    fio: "Гнездилов Денис Владимирович" },
};
function nodeEnName(node) {
  if (!node) return undefined;
  const ov = DISPLAY_NAME_OVERRIDES[node.node_id];
  return ov ? ov.en : enName(node.canonical_name);
}
function nodeTitle(node) {
  if (!node) return undefined;
  const ov = DISPLAY_NAME_OVERRIDES[node.node_id];
  return ov ? ov.fio : node.canonical_name;
}

const ROME_MODES = {
  none:          { label: "Off",                          color: "#868d97" },
  command:       { label: "Command resp. 28 / 25(3)(b)",  color: "#d98a3d" },
  appropriation: { label: "Appropriation 8(2)(a)(iv)",    color: "#cd4f43" },
  population:    { label: "Population transfer 8(2)(b)(viii)", color: "#9b7bc9" },
  aiding:        { label: "Aiding/abetting 25(3)(c)",     color: "#5aa86b" },
};
const APPROP_INSTR = new Set(["instr:ownerless_decree", "instr:court_proceedings", "instr:dnr_land_order"]);

function edgeRome(e, byId) {
  const out = new Set();
  if (e.rel === "signed" || e.rel === "issued" || e.rel === "commission_member") out.add("command");
  if (APPROP_INSTR.has(e.dst) || e.rel === "granted_land_to") out.add("appropriation");
  if (e.dst === "instr:reconstruction" || e.rel === "received_contract") out.add("population");
  if (e.rel === "received_grant" || e.rel === "received_contract" || e.rel === "granted_land_to" ||
      e.rel === "oversees" || e.rel === "directs") {
    const st = byId[e.src]?.tier, dt = byId[e.dst]?.tier;
    if (st === "commercial" || dt === "commercial" || st === "federal" || dt === "federal") out.add("aiding");
  }
  return out;
}

export default function StakeholderNetwork() {
  // ---- derived model -------------------------------------------------------
  const model = useMemo(() => {
    const byId = {};
    NETWORK.nodes.forEach((n) => (byId[n.node_id] = n));
    const outW = {}, inW = {}, inc = {};
    NETWORK.nodes.forEach((n) => (inc[n.node_id] = []));
    NETWORK.edges.forEach((e, i) => {
      const c = e.count || 0;
      outW[e.src] = (outW[e.src] || 0) + c;
      inW[e.dst] = (inW[e.dst] || 0) + c;
      if (inc[e.src]) inc[e.src].push({ e, i, dir: "out" });
      if (inc[e.dst]) inc[e.dst].push({ e, i, dir: "in" });
    });
    const weight = {};
    NETWORK.nodes.forEach((n) => (weight[n.node_id] = Math.max(outW[n.node_id] || 0, inW[n.node_id] || 0)));
    const romeByEdge = NETWORK.edges.map((e) => edgeRome(e, byId));
    return { byId, weight, inc, romeByEdge };
  }, []);

  // ---- layout --------------------------------------------------------------
  const layout = useMemo(() => {
    const pos = {};
    const COLS = 7, X0 = 80, NODE_W = 1160, ROW_H = 118, HEAD = 46, TOP = 30;
    const colW = NODE_W / COLS;
    const bands = {};
    let y = TOP;
    TIER_ORDER.forEach((tier) => {
      const list = NETWORK.nodes
        .filter((n) => n.tier === tier)
        .sort((a, b) => model.weight[b.node_id] - model.weight[a.node_id]);
      const rows = Math.max(1, Math.ceil(list.length / COLS));
      const bandTop = y;
      bands[tier] = { top: bandTop, height: rows * ROW_H + HEAD };
      list.forEach((n, i) => {
        const col = i % COLS, row = Math.floor(i / COLS);
        pos[n.node_id] = { x: X0 + col * colW + colW / 2, y: bandTop + HEAD + row * ROW_H + ROW_H / 2 };
      });
      y = bandTop + bands[tier].height;
    });
    const totalH = y + 40;
    const instr = NETWORK.nodes.filter((n) => n.kind === "instrument_class");
    const IX = X0 + NODE_W + 120;
    instr.forEach((n, i) => {
      pos[n.node_id] = { x: IX, y: TOP + ((i + 0.5) * (totalH - TOP)) / instr.length };
    });
    return { pos, bands, totalH, W: IX + 130 };
  }, [model]);

  // ---- ui state ------------------------------------------------------------
  const [selected, setSelected] = useState(null);
  const [hovered, setHovered] = useState(null);
  const [rome, setRome] = useState("none");
  const [hiddenTiers, setHiddenTiers] = useState(() => new Set());
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const [fitted, setFitted] = useState(false);
  const svgRef = useRef(null);
  const drag = useRef(null);

  const radius = useCallback((id) => {
    const w = model.weight[id] || 0;
    return Math.max(6, Math.min(44, 6 + Math.sqrt(w) * 1.15));
  }, [model]);

  // fit-to-width on mount
  useEffect(() => {
    if (fitted || !svgRef.current) return;
    const bb = svgRef.current.getBoundingClientRect();
    const k = Math.min(1, (bb.width - 20) / layout.W);
    setView({ x: 10, y: 8, k });
    setFitted(true);
  }, [fitted, layout.W]);

  const focusNode = useCallback((id) => {
    setSelected(id);
    const p = layout.pos[id];
    if (!p || !svgRef.current) return;
    const bb = svgRef.current.getBoundingClientRect();
    setView((v) => ({ ...v, x: bb.width / 2 - p.x * v.k, y: bb.height / 2 - p.y * v.k }));
  }, [layout]);

  // pan + zoom
  const onWheel = useCallback((ev) => {
    ev.preventDefault();
    const bb = svgRef.current.getBoundingClientRect();
    const mx = ev.clientX - bb.left, my = ev.clientY - bb.top;
    setView((v) => {
      const k2 = Math.max(0.2, Math.min(3, v.k * (ev.deltaY < 0 ? 1.12 : 0.89)));
      return { k: k2, x: mx - ((mx - v.x) / v.k) * k2, y: my - ((my - v.y) / v.k) * k2 };
    });
  }, []);
  const onDown = useCallback((ev) => {
    drag.current = { sx: ev.clientX, sy: ev.clientY, vx: view.x, vy: view.y };
  }, [view]);
  const onMove = useCallback((ev) => {
    if (!drag.current) return;
    setView((v) => ({ ...v, x: drag.current.vx + (ev.clientX - drag.current.sx), y: drag.current.vy + (ev.clientY - drag.current.sy) }));
  }, []);
  const onUp = useCallback(() => (drag.current = null), []);
  const zoom = (f) => setView((v) => {
    const bb = svgRef.current.getBoundingClientRect();
    const cx = bb.width / 2, cy = bb.height / 2;
    const k2 = Math.max(0.2, Math.min(3, v.k * f));
    return { k: k2, x: cx - ((cx - v.x) / v.k) * k2, y: cy - ((cy - v.y) / v.k) * k2 };
  });

  const toggleTier = (t) => setHiddenTiers((s) => {
    const n = new Set(s); n.has(t) ? n.delete(t) : n.add(t); return n;
  });

  const isHidden = useCallback((id) => {
    const n = model.byId[id];
    return n && n.kind !== "instrument_class" && hiddenTiers.has(n.tier);
  }, [model, hiddenTiers]);

  // highlight sets
  const focusId = hovered || selected;
  const litEdges = useMemo(() => {
    const s = new Set();
    if (rome !== "none") {
      model.romeByEdge.forEach((cats, i) => { if (cats.has(rome)) s.add(i); });
    } else if (focusId) {
      model.inc[focusId]?.forEach(({ i }) => s.add(i));
    }
    return s;
  }, [rome, focusId, model]);
  const litNodes = useMemo(() => {
    const s = new Set();
    if (rome !== "none") {
      NETWORK.edges.forEach((e, i) => { if (litEdges.has(i)) { s.add(e.src); s.add(e.dst); } });
    } else if (focusId) {
      s.add(focusId);
      model.inc[focusId]?.forEach(({ e }) => { s.add(e.src); s.add(e.dst); });
    }
    return s;
  }, [rome, focusId, litEdges, model]);

  const dimNode = (id) => {
    if (isHidden(id)) return true;
    if (litNodes.size && !litNodes.has(id)) return true;
    return false;
  };

  // spine resolution by name
  const spine = useMemo(() => {
    const find = (p) => NETWORK.nodes.find((n) => n.canonical_name.startsWith(p));
    return [
      { n: find("Иващенко"), date: "06.04.2022", note: "first head" },
      { n: find("Моргун"), date: "23.01.2023", note: "head" },
      { n: find("Кольцов"), date: "13.06.2025", note: "current (врио)" },
    ].filter((x) => x.n);
  }, []);
  const apex = useMemo(() => NETWORK.nodes.find((n) => n.canonical_name.startsWith("Пушилин")), []);

  const sel = selected ? model.byId[selected] : null;

  // ---- render --------------------------------------------------------------
  const C = { bg: "#0c0e11", bg2: "#14171c", bg3: "#1b1f26", rail: "#262b33", rail2: "#343b46",
    paper: "#e9e7e1", dim: "#c5c3bd", muted: "#868d97", stamp: "#c79a44", ev: "#cd4030" };
  const mono = "ui-monospace, 'SF Mono', Menlo, Consolas, monospace";

  function renderEdge(e, i) {
    if (isHidden(e.src) || isHidden(e.dst)) return null;
    const a = layout.pos[e.src], b = layout.pos[e.dst];
    if (!a || !b) return null;
    const lit = litEdges.has(i);
    const anyLit = litEdges.size > 0;
    let color = C.rail2, w = 0.6, op = anyLit ? 0.05 : 0.13, marker = "";
    if (lit) {
      color = rome !== "none" ? ROME_MODES[rome].color : C.stamp;
      w = 1.6; op = 0.92;
      marker = rome !== "none" ? `url(#mk-${rome})` : "url(#mk-hi)";
    }
    const ra = radius(e.dst);
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
    const ex = b.x - (dx / len) * (ra + 4), ey = b.y - (dy / len) * (ra + 4);
    return <line key={i} x1={a.x} y1={a.y} x2={ex} y2={ey} stroke={color}
      strokeWidth={w} opacity={op} markerEnd={marker} />;
  }

  return (
    <div style={{ background: C.bg, color: C.paper, minHeight: "100vh", fontFamily: "Georgia, serif",
      display: "flex", flexDirection: "column" }}>

      {/* header */}
      <div style={{ padding: "16px 20px 10px", borderBottom: `1px solid ${C.rail}` }}>
        <div style={{ fontFamily: mono, fontSize: 10, letterSpacing: "0.18em", textTransform: "uppercase",
          color: C.stamp, marginBottom: 8 }}>Exhibit C · Forensic actor map · Council of Europe RD4U / ICC Rome Statute</div>
        <h1 style={{ fontFamily: "Helvetica, Arial, sans-serif", fontWeight: 800, fontSize: 22,
          letterSpacing: "-0.02em", margin: "0 0 6px", lineHeight: 1.15 }}>
          Mariupol Property-Seizure Pipeline — Stakeholder Network</h1>
        <div style={{ fontFamily: mono, fontSize: 12, color: C.muted }}>
          ≈52 persons / 53 orgs / 138 relations / ~8,100 evidenced acts &nbsp;·&nbsp; command flow apex → republic → municipal → judicial → commercial, through instrument bridges
        </div>
      </div>

      {/* toolbar */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center",
        padding: "10px 20px", borderBottom: `1px solid ${C.rail}`, background: C.bg2 }}>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontFamily: mono, fontSize: 9.5, letterSpacing: "0.14em", textTransform: "uppercase", color: C.muted }}>Tiers</span>
          {TIER_ORDER.map((t) => {
            const on = !hiddenTiers.has(t);
            return <button key={t} onClick={() => toggleTier(t)} style={{ fontFamily: mono, fontSize: 11,
              cursor: "pointer", padding: "4px 9px", borderRadius: 3, border: `1px solid ${on ? TIER_META[t].color : C.rail2}`,
              background: on ? TIER_META[t].color + "22" : "transparent", color: on ? C.paper : C.muted,
              display: "inline-flex", alignItems: "center", gap: 5 }}>
              <span style={{ width: 8, height: 8, borderRadius: 8, background: TIER_META[t].color, opacity: on ? 1 : 0.4 }} />
              {TIER_META[t].short}</button>;
          })}
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontFamily: mono, fontSize: 9.5, letterSpacing: "0.14em", textTransform: "uppercase", color: C.muted }}>Rome overlay</span>
          {Object.keys(ROME_MODES).map((m) => {
            const on = rome === m;
            return <button key={m} onClick={() => setRome(m)} style={{ fontFamily: mono, fontSize: 11,
              cursor: "pointer", padding: "4px 9px", borderRadius: 3,
              border: `1px solid ${on ? ROME_MODES[m].color : C.rail2}`,
              background: on ? ROME_MODES[m].color + "22" : "transparent", color: on ? C.paper : C.muted }}>
              {ROME_MODES[m].label}</button>;
          })}
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          <button onClick={() => zoom(1.2)} style={zbtn(C, mono)}>+</button>
          <button onClick={() => zoom(0.83)} style={zbtn(C, mono)}>−</button>
          <button onClick={() => { setFitted(false); setSelected(null); }} style={zbtn(C, mono)}>reset</button>
        </div>
      </div>

      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        {/* graph */}
        <div style={{ flex: 1, position: "relative", minWidth: 0 }}>
          <svg ref={svgRef} width="100%" height="620" onWheel={onWheel} onMouseDown={onDown}
            onMouseMove={onMove} onMouseUp={onUp} onMouseLeave={onUp}
            style={{ display: "block", background: C.bg, cursor: drag.current ? "grabbing" : "grab" }}>
            <defs>
              {["hi", "command", "appropriation", "population", "aiding"].map((k) => {
                const col = k === "hi" ? C.stamp : ROME_MODES[k].color;
                return <marker key={k} id={`mk-${k}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
                  markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill={col} /></marker>;
              })}
            </defs>
            <g transform={`translate(${view.x},${view.y}) scale(${view.k})`}>
              {/* tier bands */}
              {TIER_ORDER.map((t) => hiddenTiers.has(t) ? null : (
                <g key={t}>
                  <rect x={0} y={layout.bands[t].top} width={layout.W - 60} height={layout.bands[t].height - 10}
                    fill={TIER_META[t].color} opacity={0.04} rx={6} />
                  <text x={14} y={layout.bands[t].top + 24} fill={TIER_META[t].color} opacity={0.85}
                    fontFamily={mono} fontSize={12} fontWeight="700" letterSpacing="0.12em">
                    {TIER_META[t].label.toUpperCase()}</text>
                </g>
              ))}
              {/* instrument column label */}
              <text x={layout.pos["instr:ownerless_decree"]?.x - 30} y={16} fill={C.muted}
                fontFamily={mono} fontSize={11} fontWeight="700" letterSpacing="0.1em">INSTRUMENT BRIDGES</text>
              {/* edges */}
              <g>{NETWORK.edges.map((e, i) => renderEdge(e, i))}</g>
              {/* nodes */}
              <g>{NETWORK.nodes.map((n) => {
                if (isHidden(n.node_id)) return null;
                const p = layout.pos[n.node_id];
                if (!p) return null;
                const r = radius(n.node_id);
                const isInstr = n.kind === "instrument_class";
                const col = TIER_META[n.tier].color;
                const dimmed = dimNode(n.node_id);
                const isSel = selected === n.node_id;
                const showLabel = isInstr || r >= 15 || focusId === n.node_id || isSel;
                const enNm = nodeEnName(n);
                const nm = enNm.length > 17 ? enNm.slice(0, 16) + "…" : enNm;
                const fullTitle = nodeTitle(n);
                return (
                  <g key={n.node_id} opacity={dimmed ? 0.16 : 1}
                    style={{ cursor: "pointer" }}
                    onMouseEnter={() => setHovered(n.node_id)} onMouseLeave={() => setHovered(null)}
                    onClick={(ev) => { ev.stopPropagation(); focusNode(n.node_id); }}>
                    {isInstr ? (
                      <rect x={p.x - r} y={p.y - r * 0.7} width={r * 2} height={r * 1.4} rx={3}
                        fill={C.bg3} stroke={isSel ? C.paper : col} strokeWidth={isSel ? 2.5 : 1.5} />
                    ) : (
                      <circle cx={p.x} cy={p.y} r={r} fill={col} fillOpacity={0.82}
                        stroke={isSel ? C.paper : "#0c0e11"} strokeWidth={isSel ? 2.5 : 1} />
                    )}
                    {showLabel && (
                      <text x={p.x} y={p.y + r + 11} textAnchor="middle" fill={dimmed ? C.muted : C.dim}
                        fontFamily={mono} fontSize={isInstr ? 9.5 : 8.5}>
                        {nm !== fullTitle && <title>{fullTitle}</title>}
                        {nm}</text>
                    )}
                  </g>
                );
              })}</g>
            </g>
          </svg>

          {/* legend */}
          <div style={{ position: "absolute", left: 12, bottom: 12, background: "rgba(12,14,17,0.86)",
            border: `1px solid ${C.rail}`, borderRadius: 4, padding: "8px 10px", fontFamily: mono, fontSize: 10,
            color: C.dim, display: "flex", flexDirection: "column", gap: 4, backdropFilter: "blur(4px)" }}>
            <div style={{ color: C.muted, letterSpacing: "0.12em" }}>NODE SIZE ∝ EVIDENCED ACTS</div>
            <div style={{ display: "flex", gap: 9, flexWrap: "wrap", maxWidth: 220 }}>
              {TIER_ORDER.map((t) => (
                <span key={t} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 9, height: 9, borderRadius: 9, background: TIER_META[t].color }} />
                  {TIER_META[t].short}</span>
              ))}
              <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <span style={{ width: 10, height: 7, background: C.bg3, border: `1px solid ${C.muted}` }} />Instrument</span>
            </div>
          </div>
        </div>

        {/* detail panel */}
        <div style={{ width: 320, flexShrink: 0, borderLeft: `1px solid ${C.rail}`, background: C.bg2,
          overflowY: "auto", maxHeight: 620 }}>
          {!sel ? (
            <div style={{ padding: 18, fontFamily: mono, fontSize: 12, color: C.muted, lineHeight: 1.7 }}>
              Click any node to inspect its role, evidence base, counts, and the instrument bridges it acts through.
              <br /><br />Drag to pan · scroll to zoom · use the tier and Rome-overlay controls above.
            </div>
          ) : <DetailPanel sel={sel} model={model} C={C} mono={mono} focusNode={focusNode} />}
        </div>
      </div>

      {/* command spine ribbon */}
      <div style={{ borderTop: `1px solid ${C.rail}`, background: C.bg2, padding: "12px 20px 16px" }}>
        <div style={{ fontFamily: mono, fontSize: 9.5, letterSpacing: "0.16em", textTransform: "uppercase",
          color: C.muted, marginBottom: 10 }}>Command-chain spine — every appointment personally signed by{" "}
          <span title={apex ? nodeTitle(apex) : "Пушилин Денис Владимирович"}>{apex ? nodeEnName(apex) : "Denis Pushilin"}</span></div>
        <div style={{ display: "flex", alignItems: "stretch", gap: 0, flexWrap: "wrap" }}>
          {apex && (
            <>
              <SpineCard node={apex} date="Глава ДНР" note="APEX signer" C={C} mono={mono}
                color={TIER_META.dnr.color} onClick={() => focusNode(apex.node_id)} apex />
              <SpineArrow C={C} label="appoints" />
            </>
          )}
          {spine.map((s, i) => (
            <React.Fragment key={s.n.node_id}>
              <SpineCard node={s.n} date={s.date} note={s.note} C={C} mono={mono}
                color={TIER_META.municipal.color} onClick={() => focusNode(s.n.node_id)} />
              {i < spine.length - 1 && <SpineArrow C={C} />}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* provenance */}
      <div style={{ padding: "10px 20px 18px", borderTop: `1px solid ${C.rail}` }}>
        <div style={{ fontFamily: mono, fontSize: 10.5, color: C.muted, lineHeight: 1.7, maxWidth: 880 }}>
          Built from occupation / Russian-government records, each captured with a SHA-256 hash + UTC timestamp
          (Berkeley Protocol). Node size ∝ evidenced acts; counts and date ranges are drawn from the underlying
          decree, court, land-order and contract datasets. These acts evidence the seizure system, not valid title;
          Ukraine does not recognize them.
        </div>
      </div>
    </div>
  );
}

function zbtn(C, mono) {
  return { fontFamily: mono, fontSize: 12, cursor: "pointer", padding: "4px 10px", borderRadius: 3,
    border: `1px solid ${C.rail2}`, background: C.bg3, color: C.dim, minWidth: 30 };
}

function SpineArrow({ C, label }) {
  const mono = "ui-monospace, Menlo, monospace";
  return <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "0 8px" }}>
    <span style={{ color: C.stamp, fontSize: 18, fontFamily: mono }}>→</span>
    {label && <span style={{ fontFamily: mono, fontSize: 8.5, color: C.muted, letterSpacing: "0.08em" }}>{label}</span>}
  </div>;
}

function SpineCard({ node, date, note, C, mono, color, onClick, apex }) {
  return (
    <button onClick={onClick} title={nodeTitle(node)} style={{ textAlign: "left", cursor: "pointer", background: apex ? "rgba(155,123,201,0.08)" : C.bg3,
      border: `1px solid ${apex ? color : C.rail}`, borderLeft: `3px solid ${color}`, borderRadius: 3,
      padding: "8px 12px", minWidth: 150 }}>
      <div style={{ fontFamily: mono, fontSize: 12, color: C.paper, fontWeight: 700 }}>{nodeEnName(node)}</div>
      <div style={{ fontFamily: mono, fontSize: 11, color: color, marginTop: 3 }}>{date}</div>
      <div style={{ fontFamily: mono, fontSize: 9.5, color: C.muted, marginTop: 1 }}>{note}</div>
    </button>
  );
}

function DetailPanel({ sel, model, C, mono, focusNode }) {
  const tm = TIER_META[sel.tier];
  const w = model.weight[sel.node_id] || 0;
  const incid = (model.inc[sel.node_id] || []).map(({ e, dir }) => ({ e, dir }))
    .sort((a, b) => (b.e.count || 0) - (a.e.count || 0));
  const instrLinks = incid.filter(({ e, dir }) => {
    const other = dir === "out" ? e.dst : e.src;
    return model.byId[other]?.kind === "instrument_class";
  });
  const Row = ({ k, v, title }) => v ? (
    <div title={title} style={{ display: "flex", gap: 8, fontFamily: mono, fontSize: 11.5, lineHeight: 1.6 }}>
      <span style={{ color: C.muted, minWidth: 78 }}>{k}</span><span style={{ color: C.paper }}>{v}</span>
    </div>) : null;
  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: "inline-block", fontFamily: mono, fontSize: 9, letterSpacing: "0.12em",
        textTransform: "uppercase", color: "#0c0e11", background: tm.color, padding: "2px 7px", borderRadius: 2,
        fontWeight: 700, marginBottom: 9 }}>{tm.label}</div>
      <div title={DISPLAY_NAME_OVERRIDES[sel.node_id] ? undefined : sel.canonical_name} style={{ fontFamily: mono, fontSize: 15, color: C.paper, fontWeight: 700, lineHeight: 1.3, marginBottom: 4 }}>
        {nodeEnName(sel)}</div>
      {DISPLAY_NAME_OVERRIDES[sel.node_id] && (
        <div style={{ fontFamily: mono, fontSize: 10.5, color: C.muted, marginBottom: 4 }}>{nodeTitle(sel)}</div>
      )}
      <div style={{ fontFamily: mono, fontSize: 11, color: C.muted, marginBottom: 12 }}>
        {sel.kind}{sel.roles && sel.roles.length ? " · " + sel.roles.join(", ") : ""}</div>

      <div style={{ background: C.bg3, border: `1px solid ${C.rail}`, borderRadius: 4, padding: "10px 12px", marginBottom: 12 }}>
        <div style={{ fontFamily: "Helvetica, Arial, sans-serif", fontWeight: 800, fontSize: 26, color: tm.color, lineHeight: 1 }}>
          {w.toLocaleString()}</div>
        <div style={{ fontFamily: mono, fontSize: 10, color: C.muted, letterSpacing: "0.1em", marginTop: 3 }}>EVIDENCED ACTS (max in/out)</div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 3, marginBottom: 12 }}>
        <Row k="org" v={sel.org && enName(sel.org)} title={sel.org} />
        <Row k="location" v={sel.location || sel.address} />
        <Row k="INN" v={sel.inn} />
        <Row k="OGRN" v={sel.ogrn} />
        <Row k="OGRN date" v={sel.ogrn_date} />
        <Row k="status" v={sel.status} />
      </div>

      {instrLinks.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontFamily: mono, fontSize: 9.5, letterSpacing: "0.14em", textTransform: "uppercase",
            color: C.stamp, marginBottom: 6 }}>Instrument bridges</div>
          {instrLinks.map(({ e, dir }, i) => {
            const other = dir === "out" ? e.dst : e.src;
            const otherNode = model.byId[other];
            return <div key={i} style={{ fontFamily: mono, fontSize: 11, color: C.dim, lineHeight: 1.55 }}>
              <span title={otherNode && nodeTitle(otherNode)} style={{ color: C.paper }}>{otherNode && nodeEnName(otherNode)}</span>
              {" · "}{REL_LABEL[e.rel] || e.rel}{e.count ? ` ×${e.count}` : ""}</div>;
          })}
        </div>
      )}

      <div>
        <div style={{ fontFamily: mono, fontSize: 9.5, letterSpacing: "0.14em", textTransform: "uppercase",
          color: C.muted, marginBottom: 6 }}>Relations ({incid.length})</div>
        {incid.map(({ e, dir }, i) => {
          const other = dir === "out" ? e.dst : e.src;
          const on = model.byId[other];
          const dates = e.date_min ? `${e.date_min}${e.date_max && e.date_max !== e.date_min ? " → " + e.date_max : ""}` : "";
          return (
            <div key={i} onClick={() => on && focusNode(other)} style={{ cursor: on ? "pointer" : "default",
              padding: "5px 0", borderBottom: `1px solid ${C.rail}`, fontFamily: mono, fontSize: 11, lineHeight: 1.5 }}>
              <span style={{ color: dir === "out" ? C.stamp : C.muted }}>{dir === "out" ? "▶ " : "◀ "}</span>
              <span style={{ color: C.dim }}>{REL_LABEL[e.rel] || e.rel}</span>
              {e.count ? <span style={{ color: C.paper }}> ×{e.count}</span> : null}
              <div title={on ? nodeTitle(on) : undefined} style={{ color: C.paper, paddingLeft: 14 }}>{on ? nodeEnName(on) : other}</div>
              {dates && <div style={{ color: C.muted, paddingLeft: 14, fontSize: 10 }}>{dates}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
