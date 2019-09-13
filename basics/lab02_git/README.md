Git
==========

Git stellt eine Umgebung bereit, um Code auf einem Server zentral zu speichern.
Git gibt die Möglichkeit, Quelltext mit anderen Personen zu teilen, und macht es für mehr als eine Person einfach, Code zur gleichen Datei und zum gleichen Projekt hinzuzufügen, zu ändern oder zu löschen, während eine Quelle für diese Datei erhalten bleibt.
Wie Google Docs ist Git ein Online-Portal, an dem mit anderen Leuten an Code gebastelt werden kann und nicht verschiedene Versionen hin- und hergeschickt werden müssen.

(http://try.github.io/)


Allgemeiner Überblick
=========

Definition "Version Control System"
=========
Ein **Versionskontrollsystem** (VCS) verfolgt die Historie von Änderungen, wenn Personen und Teams gemeinsam an Projekten arbeiten. Im Laufe des Projekts können Teams Tests durchführen, Fehler beheben und neuen Code einbringen, mit der Gewissheit, dass jede Version jederzeit wiederhergestellt werden kann. Entwickler können die Projekthistorie einsehen, um herauszufinden:
* Welche Änderungen wurden vorgenommen?
* Wer hat die Änderungen vorgenommen?
* Wann wurden die Änderungen vorgenommen?
* Warum waren Änderungen erforderlich?

**Bekannte Plattformen (GitHub, GitLab)**
=========
* GitLab
* Bitbucket
* Google Code
* FogBugz
* Gitea

Anlegen Repository
=========

**Besonderheiten Git:**

* Hash Codes

Distributed Version Control System
=========

Git ist ein Beispiel für ein **verteiltes Versionskontrollsystem** (**"Distributed Version Control System"**, DVCS), das häufig für die Entwicklung von Open Source und kommerzieller Software verwendet wird. DVCSs ermöglichen den vollen Zugriff auf jede Datei, jeden Zweig und jede Iteration eines Projekts und ermöglichen jedem Benutzer den Zugriff auf eine vollständige und in sich geschlossene Historie aller Änderungen. Im Gegensatz zu einst beliebten zentralisierten Versionskontrollsystemen benötigen DVCS wie Git keine ständige Verbindung zu einem zentralen Repository. Entwickler können überall arbeiten und asynchron von jeder Zeitzone aus zusammenarbeiten.

Ohne Versionskontrolle sind die Teammitglieder redundanten Aufgaben, langsameren Zeitabständen und mehreren Kopien eines einzelnen Projekts ausgesetzt. Um unnötige Arbeit zu vermeiden, geben Git und andere VCSs jedem Beteiligten eine einheitliche und konsistente Sicht auf ein Projekt und zeigen bereits laufende Arbeiten an. Eine transparente Historie der Veränderungen, wer sie vorgenommen hat und wie sie zur Entwicklung eines Projekts beitragen, hilft den Teammitgliedern, sich auszurichten und unabhängig zu arbeiten.


Clone Repository
=========


Grundlegende Git-Befehle
=========
Um Git zu verwenden, verwenden Entwickler spezielle Befehle zum Kopieren, Erstellen, Ändern und Kombinieren von Code. Diese Befehle können direkt von der Kommandozeile aus ausgeführt werden. Hier sind einige gängige Befehle zur Verwendung von Git:

*git init* initialisiert ein brandneues Git-Repository und beginnt mit der Verfolgung eines bestehenden Verzeichnisses. Es wird ein versteckter Unterordner innerhalb des bestehenden Verzeichnisses hinzugefügt, der die für die Versionskontrolle erforderliche interne Datenstruktur enthält.

*git clone* erstellt eine lokale Kopie eines Projekts, das bereits remote existiert. Der Klon enthält alle Dateien, den Verlauf und die Zweige des Projekts.

*git add* führt eine Veränderung durch. Git verfolgt Änderungen an der Codebasis eines Entwicklers, aber es ist notwendig, die Änderungen durchzuführen und eine Momentaufnahme zu machen, um sie in die Projekthistorie aufzunehmen. Dieser Befehl führt das Staging durch, den ersten Teil dieses zweistufigen Prozesses. Alle Änderungen, die durchgeführt werden, werden Teil des nächsten Snapshots und Teil der Projekthistorie. Das separate Staging und Commit gibt Entwicklern die volle Kontrolle über die Historie ihres Projekts, ohne die Art und Weise, wie sie programmieren und arbeiten, zu verändern.

*git commit* speichert den Snapshot in der Projekthistorie und schließt den Change-Tracking-Prozess ab. Kurz gesagt, ein Commit funktioniert wie das Aufnehmen eines Fotos. Alles, was mit *git add* inszeniert wurde, wird Teil des Snapshots mit *git commit*.

*git status* zeigt den Status von Änderungen als nicht verfolgt, geändert oder durchgeführt an.

*git branch* zeigt die Zweige, an denen lokal gearbeitet wird.

*git merge* verschmilzt Entwicklungslinien miteinander. Dieser Befehl wird typischerweise verwendet, um Veränderungen, die an zwei verschiedenen Zweigen vorgenommen wurden, zu kombinieren. Ein Entwickler würde beispielsweise fusionieren, wenn er Änderungen aus einem Feature-Zweig in den Master-Zweig für die Bereitstellung kombinieren möchte.

*git pull* aktualisiert die lokale Entwicklungslinie mit Updates von seinem entfernten Gegenstück. Entwickler verwenden diesen Befehl, wenn ein Teamkollege einen Zweig auf eines Remotes festgelegt hat und diese Änderungen in seiner lokalen Umgebung berücksichtigen möchte.

*git push* aktualisiert das Remote-Repository mit allen lokal vorgenommenen Commits für einen Zweig.



Commit / Revert Changes
=========

Branches
=========

Log
=========

Checkout Historic Version
=========

Stash Changes
=========

Merge / Conflict Handling
=========

Push / Pull
=========

Gitlab
=========
* Create Merge Request

* User Rights / Create Repository
