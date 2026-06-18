# Anotační příručka v3-final

**Bakalářská práce:** Trénování a kvalitativní analýza lokálních jazykových modelů s využitím vlastní datové sady
**Účel:** Konzistentní rule-based anotace zpravodajských titulků pro fine-tuning a evaluaci LLM
**Kategorie:** `NOT_MISLEADING` / `POTENTIALLY_MISLEADING` / `MISLEADING`

> **Verze v3-final** je **zjednodušená produkční verze** schématu pro samotný fine-tuning modelu. Verze v3.1 obsahovala navíc Sekci II (ověření faktů z článku) a širší metadata, která jsou ponechána jako reference pro budoucí rozšíření výzkumu (viz sekce 9 této příručky).

---

## 1. Cíl anotace

Posoudit u krátkého zpravodajského sdělení (titulek, perex, sociální příspěvek), nakolik je **zavádějící pro průměrného čtenáře bez expertních znalostí** dané domény.

Anotace probíhá **výhradně z titulku, bez čtení článku**. Tento přístup odpovídá reálnému scénáři konzumace zpravodajství na sociálních sítích a v agregátorech, kdy čtenář vidí titulek odděleně od článku, a je v souladu s cílem práce – fine-tunovat model na predikci zavádějícnosti **z titulku samotného**. Hodnocení neprobíhá podle subjektivního dojmu, ale podle definovaných polí a pravidel jejich kombinace.

### 1.1 Politická neutralita a metodologická pozice

Příručka **není** posouzením politických postojů, ideologií ani hodnocením názorové orientace zdroje. Hodnotí se výhradně **lingvistické a strukturální vlastnosti titulku** – atribuce, kvantifikace, framing, přítomnost konspiračního vzoru, citlivost domény. Politicky kontroverzní nebo silně názorové výroky **mohou** zůstat v kategorii NOT_MISLEADING, pokud splňují strukturální kritéria (jasná atribuce, věcný popis, absence dehumanizace nebo konspiračního narativu).

Cílem fine-tuningu modelu je rozpoznávat **strukturální zavádějící techniky napříč politickým spektrem**, nikoli klasifikovat zdroje podle ideologie.

---

## 2. Definice tří kategorií

### `NOT_MISLEADING`
Titulek poskytuje dostatek kontextu pro **přibližně správnou interpretaci**. Atribuce je jasná nebo událost je věcně ověřitelná. Nepřítomnost framingového aktu, dehumanizace, konspiračního narativu ani plošné dramatizace.

### `POTENTIALLY_MISLEADING`
Titulek **chybí klíčový kontext** (kvantifikace, baseline, zdroj výroku) **NEBO** je formulován s framingem (zatajený obsah, dramatizace, presupozice, vágní expertíza). Po doplnění kontextu by se **změnila míra** interpretace, ne směr. Atribuovaný extrémní výrok (kde atribuce drží přes test odstranění) sem patří také.

### `MISLEADING`
Titulek **systematicky zkresluje obraz reality**: reprodukuje konspirační narativ či symbol, dehumanizuje subjekt, používá apokalyptickou rétoriku, falešně atribuuje extrémní pozici odpůrcům, **nebo** používá strukturální chybějící atribuci (split-attribution), kde odkaz na mluvčího ve druhé větě nepokrývá silný claim v první. Po doplnění kontextu by se **změnil směr** interpretace.

---

## 3. Schéma – Sekce I (modelová pole, z titulku)

| Pole | Hodnoty | Povinné |
|---|---|---|
| `A1-scope_of_missing_context` | NONE / LOW / HIGH | ANO |
| `A2-scope_of_missing_context_type` | (multi-label, viz 3.2) | jen pokud A1 ≠ NONE |
| `A3-quantification_present` | NONE / PARTIAL / FULL | ANO |
| `B1-framing_present` | YES / NO | ANO |
| `B2-framing_type` | (multi-label, viz 3.4) | jen pokud B1 = YES |
| `B3-attribution_clarity` | CLEAR / VAGUE / MISSING / **SPLIT** | ANO |
| `C1-misinterpretation_risk` | LOW / MEDIUM / HIGH | ANO |
| `C2-likely_misinterpretation` | volný text (1 věta) | **NEPOVINNÉ** |
| `C3-conspiracy_pattern` | NONE / SYMBOL / NARRATIVE / FALSE_ATTRIBUTION | ANO |
| `D1-sensitive_domain` | NONE / HEALTH / SECURITY / FINANCE / IDENTITY / POLITICS / OTHER | ANO |
| **`E1-misleading_header_model_final`** | NOT_MISLEADING / POTENTIALLY_MISLEADING / MISLEADING | ANO |

### 3.1 `A1-scope_of_missing_context`
- **NONE** – vše podstatné pro interpretaci je v titulku.
- **LOW** – chybí drobnost (např. specifická lokalita), ale směr interpretace je správný.
- **HIGH** – chybí klíčový prvek (baseline, scope, časový rámec), bez kterého čtenář získá zkreslený obraz.

### 3.2 `A2-scope_of_missing_context_type` (multi-label, jen pokud A1 ≠ NONE)
- `MOTIVATION` – chybí důvod / motivace aktéra
- `CAUSALITY` – chybí příčinný řetězec
- `SCOPE` – chybí rozsah (kde / kolik / pro koho)
- `TIMEFRAME` – chybí časový rámec
- `PROCESS_STAGE` – chybí informace o fázi procesu (návrh / schváleno / implementováno)
- `UNCERTAINTY_LEVEL` – chybí míra jistoty (potvrzeno / spekulace / odhad)
- `STATISTICAL_BASELINE` – chybí referenční hodnota pro číslo
- `RELEVANCE_OF_ATTRIBUTE` – chybí, proč je vyzdvižený atribut relevantní (např. národnost)
- `NEGATIVE_SPACE` – chybí, co se NEdělá nebo NEstalo (alternativa, kontrafaktuál)

### 3.3 `A3-quantification_present`
Měří, zda titulek obsahuje konkrétní čísla nebo kvantifikaci.
- **FULL** – konkrétní číslo, procento, peněžní částka, údaj v jednotkách (zpravidla obsahuje číselnou hodnotu s jednotkou nebo měnou)
- **PARTIAL** – vágní kvantifikace bez číselného ukotvení (typicky neurčité množství, superlativ bez baseline, hodnotící adjektivum)
- **NONE** – bez jakékoli kvantifikace (sloveso změny bez údaje o velikosti změny)

### 3.4 `B2-framing_type` (multi-label, jen pokud B1 = YES)
- `IDENTITY_HIGHLIGHTING` – neopodstatněné zdůraznění etnicity / národnosti / náboženství aktéra
- `EMOTIONAL_LANGUAGE` – emočně zabarvený jazyk bez ospravedlnění obsahu
- `ABSOLUTE_CLAIMS` – superlativy bez ukotvení („nejhorší", „rekordní", „bezprecedentní")
- `CAUSAL_SHORTCUT` – monokauzální vysvětlení složitého jevu
- `SELECTIVE_FACTS` – výběr faktů zkreslující obraz
- `CLICKBAIT_STYLE` – zatajení klíčové informace pro kliknutí (produkt, lokalita, hodnota)
- `MULTIPLE_MEANING` – záměrná dvojznačnost
- `ATTRIBUTED_CLAIM` – citovaný extrémní výrok mimo redakční hlas
- `PRESUPPOSITION` – otázka / formulace předpokládající kontroverzní fakt
- **`DEHUMANIZATION`** – dehumanizující metafora aplikovaná na veřejné instituce, etnické či sociální skupiny nebo konkrétní aktéry. Typická lexikální pole: zoologická (zvířecí metafory, hmyz, šelmy), patologická (paraziti, nákaza, hniloba), metafory podřízenosti a sluhovství (loutky, sluhové, podřízené bytosti, vazalové), submisivní fyzické obrazy (pokoření, klečení), kriminální (organizovaný zločin nebo gangsterská terminologie aplikovaná na veřejné instituce a politické subjekty).
- **`APOCALYPTIC`** – apokalyptická / poplašná telegrafická rétorika: dramatické obrazy konce, nezvratnosti, zhroucení v krátkých větných celcích řazených sériově. Typické rysy: trojnásobná eskalace negativních predikcí, formulace o nezvratnosti, kosmické / civilizační měřítko ohrožení, ztráta naděje, srovnání se zlomovými historickými událostmi.

### 3.5 `B3-attribution_clarity`
- **CLEAR** – výrok je atribuovaný konkrétnímu mluvčímu / instituci v gramaticky pokrývajícím rozsahu (*„X řekl: …", „X: …", „… , uvedl X"*)
- **VAGUE** – atribuce je vágní (*„expert", „odborník", „lékaři", „analytik", „údaje"*)
- **MISSING** – žádná atribuce u tvrzení, které ji vyžaduje
- **SPLIT** – atribuce v druhé větě se gramaticky **nevztahuje** na hlavní claim v první větě. Charakteristický strukturální vzor: první věta = autoritativní deklarace bez uvozovek a bez slovesa typu *řekl / uvedl / tvrdí*, druhá věta = pouze rámcové uvedení mluvčího formou *„[Mluvčí] o [tématu]"* nebo *„[Mluvčí] k [události]"*. Tečka mezi větami odděluje gramatický rozsah atribuce – slovo „o" / „k" gramaticky uvádí téma, ne výrokové pokrytí předchozího claimu.

### 3.6 `C1-misinterpretation_risk`
Pravděpodobnost, že čtenář získá z titulku obraz reality, který by se po znalosti plného kontextu **lišil**.
- **LOW** – věcný titulek, malé riziko špatného pochopení
- **MEDIUM** – chybějící kontext / framing může čtenáře navést jiným směrem
- **HIGH** – pravděpodobně si čtenář odnese obraz, který je v zásadním rozporu s realitou

### 3.7 `C2-likely_misinterpretation` (NEPOVINNÉ)
**Pole je nepovinné** – můžeš ho nechat prázdné. Pokud ho vyplníš, **stačí jedna krátká věta** ve formátu „Čtenář si pravděpodobně odnese, že …".

Pole slouží jako **anotátorská reflexe** a podklad pro pozdější kvalitativní analýzu v BP. Není součástí trénovacích dat pro model. Použití doporučeno zejména u **hraničních případů** mezi POTENTIALLY a MISLEADING.

### 3.8 `C3-conspiracy_pattern`
Reprodukce konspiračního obsahu v titulku.
- **NONE** – bez konspiračního prvku
- **SYMBOL** – afirmativní zmínka konspiračního symbolu nebo termínu, který v dezinformačním ekosystému funguje jako shorthand pro celý narativ. Typické kategorie: konkrétní jmenované osoby (G. / A. Soros), instituce vnímané jako kabaly (Davos / WEF / Bilderberg), konceptuální označení plánů (Great Reset, Velká výměna / Náhrada národů, Nový světový řád), termíny pro skrytý mocenský aparát (Deep State, hluboký stát), termíny zpochybňující vědecký konsensus (klimatická lež, plandemie, farmabyznys), terminologie inscenovaných útoků (false flag), QAnon symbolika (satanské praktiky elit, pedofilní okruhy washingtonských elit).
  *Poznámka: Výčet odráží symboly dokumentované v akademické literatuře a v reportingu specializovaných institucí (např. EU DisinfoLab, Atlantic Council DFRLab) jako aktuálně rozšířené v evropském a českém mediálním prostoru. Seznam je deskriptivní, nikoli preskriptivní, a může být v budoucnu rozšířen.*
- **NARRATIVE** – reprodukce konspiračního příběhu bez explicitního symbolu. Typické okruhy: narativ s inverzí obvyklých rolí mezi geopolitickými aktéry (přesun viny mezi účastníky konfliktu); zobrazení nadnárodní instituce jako jednotného aktéra s nepřátelským plánem proti národnímu zájmu; manipulované volby jako systémový jev; plánovaná infrastrukturní krize (blackout, energetika, potraviny jako test nebo plán); stát plánující smrt nebo škodu vlastních občanů; probuzenecký rámec s tezí „skrytá pravda, kterou většina nezná"; sankce jako podvod; etablovaná média jako koordinovaný protivník čtenáře.
- **FALSE_ATTRIBUTION** – straw-man citace neexistujícího postoje: titulek **vkládá do úst** odpůrcům (často institucím – EU, OSN, vládě, „elitám") výrok, který reálně nikdy neformulovali. Typický rozpoznávací znak: dvojtečka následovaná hrozivou větou v 1. osobě plurálu (*„Uděláme..."*, *„Zlikvidujeme..."*) nebo imperativním tónem směrem ke čtenáři, vždy v kombinaci se sarkasticky zarámovanou pozicí, která má vyvolat odpor.

**Test reprodukce vs. reportáž:** Pokud titulek konspirační teorii **kriticky reportuje, vyvrací nebo o ní píše s odstupem** (typicky uvozovkami, slovem *údajný / domnělý*, atribucí konkrétnímu mluvčímu), je to NONE. Pokud ji **přebírá vlastním hlasem** redakce nebo pokud klade **sugestivní otázku, která konspirační premisu přijímá** (otázka bez kritického rámce, bez následného vyvrácení), je to SYMBOL nebo NARRATIVE.

### 3.9 `D1-sensitive_domain`
Tematická citlivost, **modulátor přísnosti** ostatních polí.
- **NONE** – neutrální téma
- **HEALTH** – zdraví, léky, nemoci, výživa, vakcíny
- **SECURITY** – válka, terorismus, extremismus, krimi s bezpečnostními dopady
- **FINANCE** – úspory, ceny, dluh, hypotéky, ekonomická predikce
- **IDENTITY** – etnicita, náboženství, gender, sexuální orientace, migrace v rámci tematizace národní příslušnosti
- **POLITICS** – vláda, volby, instituce, zahraniční politika
- **OTHER** – jiná citlivá doména

**Klíčové pravidlo:** Doména **sama o sobě neurčuje** label. Modifikuje **přísnost vyhodnocení**: v citlivé doméně klesá hranice POTENTIALLY (chybějící atribuce + dramatizace, co by jinde byla NOT, je v HEALTH/FINANCE/SECURITY POTENTIALLY). MISLEADING hranice klesá zejména u zdravotních claimů v rozporu s konsensem a u finančních / bezpečnostních claimů s konspiračním narativem.

### 3.10 `E1-misleading_header_model_final`
Finální label **z pohledu titulku**. Vyhodnocuje se **až po vyplnění A1–D1**, jako shrnutí submetrik. Viz rozhodovací pravidlo v sekci 4.

---

## 4. Rozhodovací pravidlo pro `E1`

Po vyplnění A1–D1 použij následující rozhodovací logiku:

```
1. Obsahuje titulek C3 = SYMBOL, NARRATIVE nebo FALSE_ATTRIBUTION?
   → ANO + B3 ≠ CLEAR (atribuce nezachraňuje)  →  MISLEADING
   → ANO + B3 = CLEAR (atribuce extrémnímu mluvčímu) →  POTENTIALLY

2. Je B3 = SPLIT?
   → ANO  →  MISLEADING

3. Obsahuje B2 = DEHUMANIZATION nebo APOCALYPTIC?
   → ANO + B3 = MISSING / SPLIT  →  MISLEADING
   → ANO + B3 = CLEAR (atribuovaný extrémní výrok) →  POTENTIALLY

4. Je v citlivé doméně D1 ∈ {HEALTH, FINANCE, SECURITY} a:
   - B3 ∈ {VAGUE, MISSING}
   - A3 = NONE
   - B1 = YES
   → POTENTIALLY

5. Je v doméně HEALTH a tvrzení je v rozporu s vědeckým konsensem?
   → MISLEADING

6. Vyplněno B1 = YES s některým z:
   {CLICKBAIT_STYLE, PRESUPPOSITION, ATTRIBUTED_CLAIM,
    EMOTIONAL_LANGUAGE, CAUSAL_SHORTCUT, ABSOLUTE_CLAIMS}
   → POTENTIALLY

   Výjimka (zůstává NOT): Pokud je B3 = CLEAR a obsah je
   ČISTĚ věcný popis bez dramatizace, kategorického obvinění
   skupiny nebo silně hodnotícího jazyka – viz sekce 6.1
   (atribuovaný politický postoj BEZ extrémní rétoriky).

7. A1 = HIGH (chybí klíčový kontext) NEBO A3 = NONE u trendového /
   predikčního tvrzení?
   → POTENTIALLY

8. Vše ostatní (A1 ∈ {NONE, LOW}, B1 = NO, B3 ∈ {CLEAR},
                C3 = NONE, A3 ∈ {FULL, PARTIAL})
   → NOT_MISLEADING
```

**Test obrácené interpretace** (pro hranici POTENTIALLY vs. MISLEADING):
> Kdybych doplnil chybějící kontext – změnil by se **směr** interpretace, nebo jen její **míra**?
- Změnil by se **směr** → MISLEADING
- Změnila by se jen **míra** → POTENTIALLY

**Test odstranění atribuce** (pro hranici NOT vs. POTENTIALLY u atribuovaných výroků):
> Pokud z titulku odstraním „říká X / podle X", co zbude?
- Zbude **věcný popis** → titulek je NOT (atribuce není podstatná)
- Zbude **extrémní claim** → titulek je POTENTIALLY (atribuce drží mimo MISLEADING)
- Atribuce ale **gramaticky nepokrývá první větu** → SPLIT → MISLEADING

---

## 5. Schéma – Metadata (minimum)

| Pole | Hodnoty | Povinné |
|---|---|---|
| `M1-language` | CS / EN / SK | ANO |
| `M2-topic_domain` | POLITICS / CRIME / HEALTH / ECONOMY / SOCIETY / SPORT / CULTURE / TECH / OTHER | ANO |
| `M3-annotation_confidence` | LOW / MEDIUM / HIGH | ANO |

### 5.1 `M1-language`
Jazyk titulku. SK = slovenština.

### 5.2 `M2-topic_domain`
Tematická doména titulku. **Nezávislé od `D1`**: D1 říká, jestli je téma citlivé (modulátor přísnosti); M2 říká, o čem titulek je (kategorizace pro statistiku BP).

### 5.3 `M3-annotation_confidence`
- **HIGH** – všechna pole jednoznačná, žádné pochybnosti
- **MEDIUM** – jedno až dvě pole na pomezí, ale celkový label je jasný
- **LOW** – hraniční případ; titulek je nejednoznačný; různí anotátoři by mohli rozhodnout jinak

⚠️ **Doporučení:** LOW záznamy zvážit pro **vyřazení z trénovací sady** (případně dát jen do val/test, ne train). Pro BP je užitečné mít přehled: „X % titulků mělo MEDIUM/LOW jistotu, což ukazuje na inherentní obtížnost úkolu".

---

## 6. Charakteristické vzory v jednotlivých kategoriích

### 6.1 NOT_MISLEADING – typické vzory
- **Konkrétní událost** s jasnou lokalitou, kvantifikací, atribucí (krimi, havárie, soudní rozhodnutí, sport, kultura)
- **Politické rozhodnutí** s CLEAR atribucí a věcným popisem akce
- **Atribuovaný politický postoj BEZ extrémní rétoriky** – i kontroverzní názor zůstává NOT, pokud splňuje **všechny** následující podmínky:
  - Atribuce je CLEAR (formát „Mluvčí: výrok" nebo „Mluvčí řekl, že …")
  - Výrok je **věcný popis programu, postoje, konkrétní kritiky, hodnocení faktu** – nikoli kategorické obvinění celé skupiny
  - **Není** dramatizující (žádné „pokušení totality", „katastrofální", „prohnilý", „kolaps", „pád")
  - **Není** dehumanizující (žádné metafory ze sekce 3.4 / DEHUMANIZATION)
  - **Není** konspirační (žádné symboly nebo narativy ze sekce 3.8)
  - Pokud výrok obsahuje hodnotící adjektivum nebo kategorické tvrzení o skupině → patří do POTENTIALLY (vzor P1, viz sekce 7.4)
- **Konkrétní finance/statistika** s plnou kvantifikací a atribucí
- **Servisní informace** (dopravní výluky, varování úřadů, změny ve službách) s konkrétními detaily
- **Diplomatická událost** s atribucí všech relevantních stran

### 6.2 POTENTIALLY_MISLEADING – typické vzory
- **Atribuovaný extrémní výrok** (atribuce CLEAR konkrétnímu mluvčímu, ale výrok by bez ní byl framingový akt)
- **Vágní expertní atribuce** – odkaz na neidentifikovaného odborníka, lékaře, analytika, právníka apod.
- **CLICKBAIT_STYLE se zatajeným obsahem** – produkt, lokalita, hodnota, identita zatajena pro vyvolání kliknutí
- **Otázka s PRESUPPOSITION** – otázka předpokládá kontroverzní fakt, který nebyl prokázán
- **Predikce nebo trendové tvrzení bez tří kotev** – chybí kombinace atribuce, číselné kvantifikace a časového rámce
- **Komentář / glosa s autorskou diagnózou** – žánrově legitimní, ale s hodnotící formulací
- **Modalita („prý", „má", „může")** bez ostatních kotev
- **Dramatizace bez atribuce** v běžných situacích
- **Kolektivní subjekt** bez atribuce nebo kvantifikace

### 6.3 MISLEADING – typické vzory
- **SPLIT atribuce** – silný claim v první větě, jen rámcová atribuce ve druhé („[Mluvčí] o [tématu]")
- **Konspirační symbol nebo narativ** – viz katalog v 3.8
- **Dehumanizace** – aplikace dehumanizujících metafor (zvířecí, parazitické, sluhovské, submisivní, kriminální) na veřejné instituce nebo konkrétní aktéry
- **Falešná atribuce extrémní pozice** – straw-man citace, kterou odpůrci nikdy nevyřkli
- **Apokalyptická / poplašná rétorika** – sériová eskalace negativních predikcí v telegrafickém stylu
- **Obrácení reality** – titulek tvrdí opak ověřitelného stavu
- **Zdravotní / vědecká dezinformace** v rozporu s konsensem
- **Sériové autoritativní obvinění** bez atribuce s extrémní rétorikou

---

## 7. Hraniční případy a pravidla pro jejich řešení

### 7.1 Atribuovaný extrémní výrok obsahující konspirační symbol
*Schéma: „Mluvčí: [extrémní claim s konspiračním symbolem]"*
- C3 = SYMBOL/NARRATIVE, B3 = CLEAR
- E1 = **POTENTIALLY** (atribuce drží přes test odstranění)

### 7.2 Otázka jako sugestivní reprodukce
*Schéma: „[Konspirační teze]?"*
- Pokud otázka **přijímá konspirační premisu**: C3 = SYMBOL/NARRATIVE, E1 obvykle MISLEADING
- Pokud otázka **kriticky zpochybňuje**: C3 = NONE

### 7.3 Komentář / glosa s autorskou diagnózou
*Schéma: „Komentář: [autorská hodnotící formulace]"*
- Žánrově je autorská hodnocení legitimní → B1 obvykle YES, ale pouze EMOTIONAL_LANGUAGE / ATTRIBUTED_CLAIM
- E1 = **POTENTIALLY** (žánrová hodnota zachraňuje před MISLEADING, pokud chybí konspirační prvek)

### 7.4 Atribuovaný politický komentář s hodnotící rétorikou
*Schéma: „Mluvčí: [hodnotící politický výrok bez dehumanizace nebo konspirace]"*

Toto je častý hraniční případ. Klíčové rozhodovací kritérium je, **zda je výrok věcný politický postoj, nebo silně hodnotící / dramatizující obvinění**.

**Test obsahu výroku:**
- **Věcný politický postoj** (NOT_MISLEADING) – výrok popisuje program, postoj, hodnocení politiky bez dramatizace nebo kategorického obvinění celých skupin. Příkladem je formulace typu „X navrhuje řešení Y", „X hodnotí situaci jako Y", „X kritizuje politiku Y".
- **Hodnotící / dramatizující obvinění** (POTENTIALLY) – výrok obsahuje **alespoň jeden** z následujících rysů:
  - Kategorické obvinění celé politické / ideologické skupiny (např. tíhnutí k totalitě, zradě, korupci, manipulaci, lži jako kolektivní vlastnost skupiny)
  - Dramatizující formulace o „pokušení", „pádu", „zradě", „zhroucení", „kolapsu", „katastrofě"
  - Kategorické tvrzení o důsledcích bez kvantifikace (*„povede ke zničení X"*)
  - Hodnotící adjektiva v atribučně-rámujícím postavení (*„katastrofální politika"*, *„bezohledný plán"*)

**Vyhodnocení:**
- B3 = CLEAR (atribuce je jasná, formát „Mluvčí: …")
- B1 = YES, B2 = ATTRIBUTED_CLAIM + případně EMOTIONAL_LANGUAGE
- C3 = NONE (žádný konspirační symbol nebo narativ)
- D1 = POLITICS

**E1 = POTENTIALLY** – protože výrok by bez atribuce byl framingový akt (vzor P1). Atribuce drží titulek mimo MISLEADING, ale ne mimo POTENTIALLY. Toto rozhodnutí je v souladu s testem odstranění atribuce ze sekce 4.

**Hraniční výjimka – kdy zůstává NOT:**
Pokud výrok je čistě věcný (program, návrh, hodnocení faktu, kritika konkrétního rozhodnutí konkrétní instituce) **bez** dramatizujícího jazyka a **bez** kategorického obvinění skupiny, zůstává NOT (sekce 6.1).

### 7.5 Tabloidní styl s vykřičníky a kapitálkami
- Vykřičníky a dramatizace samy o sobě **nejsou** framing, pokud jen popisují konkrétní událost
- Pokud věcně popisuje událost (krimi, havárie) s lokalitou a fakty: B1 = NO, E1 = NOT
- Pokud dramatizace **zatajuje klíčový obsah**: B2 = CLICKBAIT_STYLE, E1 = POTENTIALLY

### 7.6 Pejorativ vs. konspirační symbol
- **Pejorativ / dehumanizující metafora** → patří do **B2 = DEHUMANIZATION**, ne do C3
- **Konspirační symbol** je o **strukturálním příběhu o skrytém plánu**, ne o nadávkách

### 7.7 Modalita „prý" / „má" / „může"
- Modalita zachraňuje jen jeden rozměr
- Pokud titulek zároveň postrádá atribuci A KVANTIFIKACI: E1 = POTENTIALLY
- Pokud navíc obsahuje konspirační narativ: E1 = MISLEADING

### 7.8 Slovenština
- Slovenské titulky → `M1-language = SK`, stejná pravidla jako pro češtinu

---

## 8. Postup anotace (workflow)

Anotace probíhá **v jednom kroku** – anotátor vidí pouze titulek a vyplňuje Sekci I + minimum metadat:

1. **Přečti titulek.**
2. **Vyplň Sekci I postupně po blocích A → B → C → D**, **až poté** rozhodni `E1-misleading_header_model_final`. Pole `C2-likely_misinterpretation` je **nepovinné** – vyplň jen u hraničních případů.
3. **Doplň Metadata:** `M1-language`, `M2-topic_domain`, `M3-annotation_confidence`.

**Časový limit:** ~1 minuta na záznam. Záznamy překračující 3 minuty označit `M3 = LOW`.

**Princip průměrného čtenáře:** Hodnocení probíhá z perspektivy průměrného českého čtenáře bez expertních znalostí dané domény. Čtenář **nezná** odborné termíny, statistické baseline ani historický kontext mimo všeobecné povědomí; **neověřuje** fakta – bere titulek tak, jak je.

---

## 9. Vztah k širšímu výzkumu (rozšíření v3.1)

Anotační schéma navržené v této práci se zaměřuje na rozpoznání zavádějícnosti **čistě z titulku**, což odpovídá reálnému scénáři konzumace zpravodajství na sociálních sítích a v agregátorech.

Pro robustnější ground truth by bylo možné v dalším výzkumu rozšířit anotační proces o **druhou fázi**, ve které anotátor ověřuje fakta z článku (Sekce II z verze v3.1):

- `F1` – factual_correctness (TRUE / FALSE / UNVERIFIABLE)
- `F2` – factual_error_degree (MINOR / MAJOR)
- `F3` – temporal_validity (CURRENT / OUTDATED / UNCLEAR)
- `F4` – context_availability (IN_SOURCE / EXTERNAL_SOURCES / NOT_AVAILABLE)
- `G1` – korigovaný label po čtení článku

Toto rozšíření by umožnilo:
1. Studovat rozdíly mezi **strukturální a faktickou** zavádějícností
2. Trénovat **dvoukrokový model** (titulek → article-aware predikce)
3. Měřit, kolik % zavádějících titulků je **faktických ve vlastním tvrzení**, ale zavádějících v rámci/atribuci

Pro účely této bakalářské práce a její scope však toto rozšíření **není relevantní** – model je trénován výhradně na titulkovou predikci. Plné schéma je dokumentováno ve verzi v3.1 příručky.
