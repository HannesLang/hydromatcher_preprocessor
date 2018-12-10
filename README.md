**hydromatcher_preprocessor** 

Preconditions
- provide a passwordfile for postgresql in c:\Users\username\AppData\Roaming\postgresql\pgpass.conf
- ...

**MobiLab Projekt**

In MAARE+ gibt es rund 700 Überflutungsebenen. Pro FloodPlain gibt es in den meisten Fällen 1 Zufluss.
Für diesen werden verschiedene synthetische Abflussganglinien ermittelt (Sommer, Winter, verschiedene Abflussmengen bzw Pegel).
Pro Ganglinie werden dann die resultierenden Überflutungsflächen bzw -Ebenen modelliert.
Dies wurde bisher für rund 15 Überflutungsebenen gemacht.

Ziel ist, für eine prognostizierte Abflussganglinie den besten Match
der synthetischen Ganglinien (Nearest Neighbour etc) und damit die entsprechende Überflutungsfläche zu finden.

Bei Ebenen mit einem Gefälle von mindestens 2% reicht im Allgemeinen der Qmax für ein Matching. Aber
bei flacheren Ebenen ist eben auch die Form der Ganglinie relevant.

Matching der beiden Ganglinien:
1. Interpolation der Messpunkte via scipy (vermutlich 1D) https://stackoverflow.com/questions/44805684/pattern-matching-or-comparing-two-graphs-line-charts, damit beide Graphen die gleichen Messpunkte (x-Achse) haben

Kriterien für Matching:
- Peak/Volumen-Verhältnis
- Normalisierte Ganglinie (Zeit 0 - 100%, Messpunkte z.Bsp. in 10%-Schritten; analog für Abfluss)

Neue Anforderung 28.11.2018:
Es sollen alle in einem Verzeichnis gefundenen Ganglinien (für ein schweizweites Niederschlags- bzw Überschwemmungsereignis) wie oben prozessiert werden und die gefundenen Shapes in ein einziges Shape und evtl geojson/topojson gemerged und dargestellt werden.

Jede FloodPlain bekommt eine eindeutige Id. Die Prognose-Hydrographen haben dann das Namenspattern
name_...,
Beispiel: verlue_...
Siehe auch Tabelle t_floodplain

Dissolve:
`create table t_mergeshape_union_test as
SELECT ST_Union(geom) AS geom, max_depth FROM public.t_mergeshape_181206_144554 GROUP BY max_depth;
commit;`


