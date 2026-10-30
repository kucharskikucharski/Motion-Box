# Motion Box - lista rzeczy do zrobienia

Znaczniki: [x] zrobione  [~] częściowo / placeholder  [ ] do zrobienia  [?] trzeba zdecydować.
Aktualizowane przy każdej wersji. Powtórzenia z wiadomości są scalone.

## Gotowe w wersji z dzisiaj
- [x] Zmiana nazwy warstwy dwuklikiem (timeline i Layers); odwołania (matte, IK, ekspresje) idą za nową nazwą
- [x] Jeden bounding box przy zaznaczonej warstwie (przylega do rysunku, bez ramki wielkości artboardu)
- [x] Pędzel: grubość linii = Size, kolor = przednia próbka koloru; [ i ] zmieniają rozmiar, przytrzymanie przyspiesza
- [x] D = kolory domyślne (biały / czarny), X = zamiana kolorów
- [x] Shift przy przesuwaniu: oś wybierana raz i trzymana
- [x] Ctrl+C / Ctrl+X / Ctrl+V (wkleja do zaznaczonej warstwy wektorowej, bez zaznaczenia tworzy nową; na pozycję kursora), prawy przycisk na obiekcie: Cut / Copy / Paste / Duplicate / Move to new layer / Delete
- [x] Ctrl+Z zachowuje zaznaczenie
- [x] Toolbox na sztywno w jednej kolumnie, brakujące narzędzia w strzałce na dole
- [x] Prawy przycisk na warstwie: Trim start / end to playhead, Cut at playhead, Remove trim
- [x] Rigowanie: Object > Create Skeleton from Selection (kości z anchorów i hierarchii, jak Tahoma), Drive by controller (pegi i twarz podążają za joystickiem z mnożnikiem, ujemny = przeciwnie)
- [x] Klawisze P / R / T / S na timeline pokazują pozycję / rotację / krycie / skalę zaznaczonych warstw (Shift dodaje)
- [x] Keyframe z ciemnym konturem, powiększa się po najechaniu
- [x] Footage: Replace (Ctrl+H), Show in file explorer, pytanie o sekwencję (check); Preferences: Clean cache

## Gotowe w poprzedniej wersji (do przeklikania)
- [x] Warstwy: + w timeline (lub Object > New Layer) pyta Vector / Raster. Kształty i pędzel rysują WEWNĄTRZ warstwy wektorowej (jedna warstwa = wiele obiektów). Raster: pędzel maluje piksele, gumka kasuje, zapis do assets/
- [x] Anchor point: narzędzie Anchor (Y, w slocie Transform), Ctrl = magnes do rogów / krawędzi / środka / środka artboardu; Object > Reset Anchor Point
- [x] Magnes przy przesuwaniu (Ctrl): krawędzie i środki innych obiektów oraz artboardu
- [x] Kości: kontur w własnym kolorze (Properties > Stroke / Fill), staw na początku kości, łańcuch jak w Blenderze (kolejna kość startuje na końcu poprzedniej; Esc lub zmiana narzędzia kończy)
- [x] Controllery liniowe: Position (strzałki), Rotation (łuk), Position + Rotation; reszta zablokowana. Pola "Label" (podpis nad sliderem / controllerem) w Properties
- [x] Joysticki: ramka = zaokrąglony kwadrat (XY) lub pigułka (X / Y), bez rotacji, skala tylko proporcjonalna, gałka nie wychodzi poza ramkę
- [x] Peg (przezroczysty rodzic do skryptów / ekspresji), + Null i + Peg w Schematic
- [x] Alpha matte: Properties > Track matte (wybór warstwy + Invert). Warstwa-maska znika z widoku i renderu
- [x] Ekspresje: podpowiedzi przy pisaniu (Tab wstawia, strzałki wybierają), nazwy warstw w layer("...")
- [x] Render: Ctrl+M / File > Export Render (H.264 mp4 przez ffmpeg, bez ffmpeg: sekwencja PNG)
- [x] Timeline: numery warstw, linia pokazująca gdzie wyląduje przeciągana warstwa, trim końca z keyframe'm naprawiony, prawy przycisk na warstwie (Group, Fold, Lock, Hide), ukryj / zablokuj grupę naraz, markery (M, dwuklik = tekst i kolor)
- [x] Zamykanie: pytanie Save / Discard Changes / Cancel; Autosave w Preferences (check + minuty)
- [x] Nody: podświetlenie celu przy łączeniu, białe podpisy ze skróceniem "..", więcej światła, Fit all, miniatury wszystkich nodów
- [x] Kursory: ikony narzędzi, kółko pędzla ([ i ] zmieniają rozmiar), strzałki skalowania i łuk rotacji
- [x] Fill bucket: Fill / Stroke / All (Rect i Lasso: wkrótce), Eyedropper, Scissors (cięcie warstwy na playheadzie), Zoom, Select Whole Level
- [x] Onion skin: ile klatek wstecz / w przód (prawy przycisk na ikonie cebuli)
- [x] Kłódki otwierają się i zamykają, okna startowe na środku ekranu, nowy projekt: ikona łańcucha, lista FPS, foldery (assets, graphics, palettes, scenes, scripts, renders, library)
- [x] Toolbox ze szkicu: 2 kolumny gdy brakuje miejsca (placeholdery: Artboard, Text, Taper, Lipsync, Multiline, IK, Rotate View)

## Z testu rigu oczu - następna runda (w kolejności bólu)
Pola tekstowe (wszystkie)
- [ ] Kursor w tekście: klik lub strzałki zdejmują zaznaczenie całości, edycja jednej litery; Ctrl+C / Ctrl+V tekstu ekspresji
Tworzenie i edycja obiektów
- [ ] Alt przy rysowaniu kształtu i przy skalowaniu = od środka
- [ ] Wklejanie warstw na timeline nie przesuwa reszty; nulle / pegi wklejane na środek artboardu (nie pod oryginałem)
- [ ] Ctrl+Z nie rozrzuca obiektów (zachować układ nodów i stan paneli przy cofaniu)
- [ ] Pegi z bounding boxem także w stanie niezaznaczonym (jak nulle)
- [ ] Kolor podpisu (Label) sliderów i joysticków
- [ ] Narzędzie Animate (zaznacza tylko pegi albo tylko controllery)
Nody (Schematic)
- [ ] Miniatury pokazują prawdziwy rysunek warstwy (teraz fioletowy prostokąt)
- [ ] Zaznaczanie i usuwanie połączeń (kabli) między nodami
- [ ] Węzeł Table jako korzeń sceny + strzałki kierunku na kablach (co jest rodzicem, a co dzieckiem)
- [ ] Podpinanie kilku zaznaczonych nodów naraz do jednego rodzica (warstwa z rysunkiem + peg)
- [ ] Zoom out dalej (teraz do 40%)
- [ ] Przesuwana belka między viewerem a panelem po prawej (Schematic, Drawing, Expressions)
Timeline
- [ ] Zmiana liczby klatek sceny nie wydłuża istniejących warstw
- [ ] Podświetlone, zaokrąglone krawędzie warstwy przy najechaniu (łatwiejszy trim)
- [ ] Przesuwanie całej warstwy w czasie (przód / tył)
- [ ] Parent to... w menu prawego przycisku na warstwie
Panel Drawing / okno startowe
- [ ] Stałe koło barw w panelu Drawing (pod paletą), ta sama belka do przesuwania
- [ ] Okno startowe: równe marginesy lewy / prawy, przycisk Create wyrównany do prawej krawędzi list
Pytania do wyjaśnienia (opisane w rozmowie): mnożniki przez ekspresje (Drive by controller), maska (Track matte)

## Rigging w stylu Duika
- [x] Create IK (narzędzie bone_ik): klik w dolną kość łańcucha z dwóch kości -> controller na końcu, kości podążają; Properties: Flip IK / Remove IK
- [ ] Bones -> Controllers jednym kliknięciem (controller na kość, FK)
- [ ] Przełącznik FK / IK, pole biegunowe (pole) dla kolana / łokcia
- [ ] Constraints: Orient, Look At, Path
- [ ] Auto-rig: szablony kończyn (ramię, noga: 2 kości + IK + controller)
- [ ] Struktury (cała postać), sprężyny i wiggle jako gotowe efekty
- [ ] IK dla dłuższych łańcuchów (3+ kości)

## Następne (kolejność proponowana)
1. Próbny rig postaci (Twój test) - zgłoś wszystko, co przeszkadza
2. Lipsync (patrz niżej)
3. Footage: widok siatki i listy, wyszukiwarka, nagłówek z informacją o kompozycji (wg Twoich screenów)
4. Level strip: fixed onion (niebieskie kulki) i ruchome (żółte), tryb "wejdź w level"
5. Toolbox: Twoje PNG-i, flyouty wg szkicu (Tahoma-style), Taper / Join
6. Pen + Beziery, Control Point Editor, Multiline
7. Docki przeciągane jako zakładki
8. Efekty (panel + nody), FX on/off
9. Camera + Table w nodach, widok 3D
10. Precomp, time stretch / repeat / reverse, wideo i audio

## Lipsync (plan na podstawie panelu z Tahomy)
- Narzędzie Lipsync (ikona dymka) przy zaznaczonej warstwie z fazami ust
- Okno: źródło dźwięku (plik + Play), pole na tekst (poprawia dokładność), siatka 10 głosek: A I, E, O, U, F V, L, M B P, W Q, C D G K N R S Th Y Z, Rest
- Każda głoska ma miniaturę fazy i strzałki < > do wyboru, którą fazę pokazać
- Wynik: warstwa przełącza fazy w czasie (keyframe'y faz)
- Rozpoznanie głosek z audio: najpierw import pliku danych (Rhubarb / Papagayo), potem opcjonalnie automat
- Wymaga: odtwarzania audio (pygame.mixer) i mapowania "faza -> klatka" na warstwie

## Pomysły od Ciebie (zapisane)
- Panel skryptów jak w Tahomie (HKP): wczytywanie skryptów, keyframe na zaznaczonych warstwach [~ przyciski keyframe są]
- Panel pod timeline: time stretch, repeat, reverse + widok z poziomu precompa
- Timeline na drugi monitor (wymaga zmiany biblioteki okien, np. Qt)
- Linijki (Ctrl+R) i guides, Tools w menu ze skrótami [~ menu Tools jest]
- Anchor + magnes również dla guides i linijek
- Cut tool na timeline, przyciąganie z Shift (keyframe'y, krawędzie warstw)
- Work area do renderu (B / N jak w AE), edytowalne skróty (Edit > Keyboard Shortcuts)
- Opcje ikon widoku w stylu Tahomy, panel 3D
- Przeprojektowanie okna Load (potrzebny wzór / szkic)
- Splash: wrzuć nowy PNG na prostokącie do assets/splash.png (układ napisu "Ready to launch" jak dotąd, inny układ opisze assets/splash.json)

## Workflow z Tahomy do odtworzenia (Twoje notatki)
- Maska oka: Pupil maskowany kształtem oka -> u nas Track matte
- Pupil_L / Pupil_R -> Pupil_Controller -> Face_Controller (nody)
- Rozmiar źrenic: Scale = `layer("Pupil_Size_Controller").y` (w Tahomie Col34.y)
- Blokada osi: wyrażenie `0`; albo gotowy Controller (Position / Rotation / Pos + Rot)
- Powieki: zielone prostokąty maskowane przez Eye, sterowane przez Eyelid_Controller_UP / _DOWN

## Znane ograniczenia
- Wersja była testowana tylko na atrapie pygame - błędy zgłaszaj z crash.log
- Wideo / audio: tylko linki, bez odtwarzania
- Rect i Lasso dla Fill bucket, Pen, Text, Taper, Lipsync, Artboard, Multiline, IK: placeholdery
- Raster: bez cofania (Ctrl+Z nie obejmuje pikseli), bez wiaderka
- Ponowny import tego samego pliku tworzy duplikat

## Z ostatniej rundy (do zrobienia)
- [ ] Zaznaczanie klatek na warstwie (Shift + klik: zakres), przenoszenie zaznaczenia (czerwone = zakaz upuszczenia na warstwę z rysunkami), wytnij / wklej / podmień / usuń klatki
- [ ] Przeciąganie phase'ów z Level Strip na timeline (wstawianie lub podmiana, także na zaznaczony zakres klatek)
- [ ] Tryb izolacji po kliknięciu miniatury w Level Strip (odtwarzanie, rysowanie z onion skin)
- [ ] Toolbox budowany przez przeciąganie ikon (Preferences > Tools): na razie lista narzędzi z nazwami
- [x] Preferences w działach (General, Interface, Labels, Tools, Preview, Onion Skin) + Search
- [x] Properties: miniatura warstwy, mniejszy przycisk Link to Parent
- [x] Kopiuj / wklej: kopia w tej samej warstwie +10 px, w innej warstwie w tym samym miejscu, zawsze osobny obiekt
- [x] Strzałki przesuwają zaznaczenie o 1 px (Shift 10); po kliknięciu timeline sterują playheadem
- [x] Rename wielu warstw (Ctrl+R): zastąp + sufiks (_# = numer kolejny)
- [x] Ikony narzędzi w stanach Default / Hover / Active (np. select_default.png, select_hover.png, select_active.png)
- [x] Splash: animowany status znajdowany automatycznie przy kropce (lewy dolny róg także)
- [x] Znacznik "a" na warstwie, która jest alfą innej; opcja "Show the matte layer too"

## Zgłoszone przez użytkownika, jeszcze do zrobienia (stan: 28.10.2026)
- Kości: Edit Skeleton (przesuwanie początków/końców, magnes do anchorów i końców innych kości), limit kąta zgięcia + łuk, widok kości jako kropki, "Show only active skeleton", szkielet humanoidalny jednym kliknięciem
- IK: kierunek zgięcia jako wartość skokowa (keyframe bez przejść) + wygodniejsze tworzenie (baner z krokami)
- Timeline: zaznaczanie pojedynczych klatek (Shift = wiele warstw), przesuwanie/usuwanie, zmiana fazy klawiszami W/Q, strzałki góra/dół przy warstwie z wieloma fazami, wyszukiwarka + filtr typu, przesuwana szerokość kolumny z nazwami, skracanie wielu warstw naraz
- Level Strip: pierwszy rysunek od razu na liście, rysowanie na pustej klatce tworzy nową fazę, przeciąganie faz na puste klatki (zajęte zablokowane)
- Selekcja: filtr Select (rysunki / pegi / nulle), zaznaczanie tekstu myszą w polach
- Schematic: wstawianie node'a na połączenie, zmiana nazwy dwuklikiem, podświetlenie warstwy po najechaniu na node
- Grupy: tryb izolacji (dwuklik w grupę, Esc), prawdziwy Precompose
- Joystick: zakres ruchu z czterech keyframe'ów (jak w After Effects)
- Paleta: foldery i nazwy kolorów
- Menu skrótów z wizualizacją klawiatury
- Ikony: brakuje Transform, Peg, Edit Skeleton, Animate; Gradient czeka na narzędzie

## Dodane 28.10.2026 (wieczór), jeszcze otwarte
- Library: miniatury z prawdziwą zawartością, foldery, przeciąganie w obie strony (do biblioteki i ze sceny)
- Nodey: grupa jako ramka z zachowaną hierarchią, rozwijana z menu podręcznego, kolor ramki i miniatura; czcionki i plugi skalowane razem z zoomem widoku
- Zegarek przy wartościach jest też w panelu Properties (na razie tylko na timeline)
- Timeline: właściwości wartości pokazują się klawiszami P / R / S / T / U; warto dodać prawy klik "Pokaż właściwości" i wspólny wiersz "Transform"

## Zgłoszone 29.10.2026, jeszcze otwarte
- Pozycja X i Y jako jedna wartość "Position" z opcją rozdzielenia (prawy klik)
- Faza (rysunek) sterowana sliderem - wymaga modelu rysunków/faz (cels) i Level Stripa
- Paleta: foldery, nazwy kolorów, trzy widoki (kółka / kafelki z nazwą / lista)
- Library i Footage: zaznaczanie wielu elementów, przeciąganie między timeline / viewerem a biblioteką
- Zaznaczanie tekstu myszą w polach tekstowych
- Gradient (narzędzie albo opcja w kolorach)

## Zgłoszone 30.10.2026, jeszcze otwarte
- Zaznaczanie klatek na warstwie (pojedynczych, kilku, Shift) z przesuwaniem / usuwaniem / wycinaniem / wklejaniem i zmianą fazy klawiszami W / Q
- Level Strip: zaznaczanie fazy prostokątem; panel Library z takim samym podglądem i odtwarzaniem
- Rysowanie na pustej klatce samo tworzy nową fazę; warstwy rastrowe z wieloma fazami
- Select: wspólny bounding box wielu zaznaczonych obiektów (skala, pozycja, rotacja); Animate: ikona rombu, animacja całych warstw i nulli
- Nody: wstawianie noda między Table a pozostałe
- Narzędzie Text

## Zrobione 30.10.2026 (podczas nieobecności użytkownika)
- Library: prawdziwe miniatury, zaznaczanie wielu (Shift / Ctrl), foldery, przeciąganie z biblioteki do viewera / timeline i z timeline / viewera do biblioteki
- Footage: zaznaczanie wielu, przeciąganie na scenę
- Explorer: zaznaczanie wielu plików, "Import selected", opcja "Import numbered files as a sequence"
- Paleta: nazwy kolorów, foldery, trzy widoki (kółka / kafelki z nazwą / lista)

## Nadal otwarte
- Zaznaczanie klatek na warstwie (move / delete / cut / paste, W / Q), pozycja X i Y jako jedna wartość z opcją rozdzielenia, zaznaczanie tekstu myszą, gradient, narzędzie Text, grupy w nodeach
