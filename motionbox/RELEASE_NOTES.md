# Motion Box - update 2026-10-31 (on top of alpha 4)

## Nowe
- **Level Strip jako prawdziwa pula rysunków** - każdy rysunek jest niezależny, warstwa zawsze ma co najmniej jeden (pusty) kafelek, rysunki zostają w panelu, dopóki ich tam nie usuniesz. Kolejność zmieniasz przeciąganiem (kreska pokazuje miejsce), widok siatki lub listy z dużymi miniaturami, miniatura podąża za kursorem podczas przeciągania.
- **Auto-create** - rysowanie w klatce, w której nie zaczyna się rysunek, tworzy nowy rysunek zamiast rysować po starym (także w pierwszej klatce).
- **Zaznaczanie klatek na warstwie** - klik / przeciągnięcie prostokąta (Shift dodaje), zaznaczone klatki się rozjaśniają; przeciągnięcie przesuwa, Del opróżnia, Ctrl+C / X / V kopiuje, wycina i wkleja; Alt + przeciągnięcie przesuwa całą warstwę.
- **Q / W - Drawing Substitution** - podmiana rysunku w klatce (lub w zaznaczonych klatkach) na poprzedni / następny z Level Strip. Nic nie tworzy.
- **Przeciągnięcie rysunku z Level Strip na timeline** podmienia tylko klatkę, na którą go upuścisz (albo wszystkie zaznaczone klatki).
- **Flip** - prawy klik na zaznaczonych kształtach: odbicie w poziomie lub w pionie.
- **Wyszukiwarka warstw** na timeline z filtrem typu i licznikiem; ogólne oko i kłódka nad listą warstw; jeden przycisk "+" (Drawing / Peg / Null).
- **Paleta kolorów** - nazwy (dwuklik), foldery, trzy widoki (kółka / kafelki / lista), osobne przewijanie, koło barw na sztywno; zakładki Colors i Level Strip.
- **Pędzel** - linia na żywo ma grubość i kolor rysowanej kreski, nowe pole "Smooth" wygładza drgania.
- **Onion skin** - grubość konturu rysunku, stonowane półprzezroczyste kolory, tylko zaznaczone warstwy i ich dzieci.
- **Select / Animate: "Only this layer"** - pracujesz tylko w obrębie zaznaczonej warstwy.
- **Rig** - generator warstw ciała i "Do the rig" (kości, IK), Animate Bones traktuje kość i podpięte rysunki jako jedno.
- **Biblioteka i import** - prawdziwe miniatury, wiele zaznaczonych, foldery, przeciąganie w obie strony, import wielu plików i sekwencji.
- **Skróty** - [ i ] = work area, I = eyedropper, O = elipsa, Ctrl+0 = fit, lista zoomu pod viewerem, Alt+[ / Alt+] przycinają warstwę do playheada.
- **Jedno okno programu** - drugie uruchomienie pokazuje pierwsze okno.

## Poprawki
- Kolor z toolboxu i palety nie przemalowuje już zaznaczonych obiektów (maluje Fill Bucket albo panel Properties).
- Slidery i joysticki mają przezroczyste wypełnienie i grubszy kontur.
- Nazwy warstw na timeline kończą się wielokropkiem i nie wchodzą na strzałkę rodzica; znaczniki faz to czarne kropki i kreski, ukryte przy dużym oddaleniu; siatka timeline pojawia się dopiero przy odpowiednim zbliżeniu.
- Naprawione zawieszanie programu przy przeciąganiu warstw (znikało menu).
- Wklejanie hexów ze schowka systemowego.
