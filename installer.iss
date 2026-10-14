#define AppName "Nova Office"
#define AppVer "1.0.0"
#define Exe "NovaOffice.exe"

[Setup]
AppId={{B1C4A6F2-5E1D-4B7A-9C3E-7A2D8F10C5E1}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=Nova
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=Output
OutputBaseFilename=NovaOffice-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#Exe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; Flags: unchecked
Name: "assoc"; Description: "Добавить Nova Office в «Открыть с помощью» и в список программ по умолчанию (PDF, PPTX, DOCX, TXT, MD)"

[Files]
; Все зависимости (Python, Qt, PyMuPDF, python-docx, python-pptx) уже внутри папки сборки
Source: "dist\NovaOffice\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#Exe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#Exe}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\NovaOffice.File"; ValueType: string; ValueData: "Документ Nova Office"; Flags: uninsdeletekey; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\NovaOffice.File\DefaultIcon"; ValueType: string; ValueData: "{app}\{#Exe},0"; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\NovaOffice.File\shell\open\command"; ValueType: string; ValueData: """{app}\{#Exe}"" ""%1"""; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\Applications\{#Exe}\shell\open\command"; ValueType: string; ValueData: """{app}\{#Exe}"" ""%1"""; Flags: uninsdeletekey; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "NovaOffice.File"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\.pptx\OpenWithProgids"; ValueType: string; ValueName: "NovaOffice.File"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\.docx\OpenWithProgids"; ValueType: string; ValueName: "NovaOffice.File"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\.txt\OpenWithProgids"; ValueType: string; ValueName: "NovaOffice.File"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\.md\OpenWithProgids"; ValueType: string; ValueName: "NovaOffice.File"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\NovaOffice\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#AppName}"; Flags: uninsdeletekey; Tasks: assoc
Root: HKA; Subkey: "Software\NovaOffice\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "PDF, презентации и документы"; Tasks: assoc
Root: HKA; Subkey: "Software\NovaOffice\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pdf"; ValueData: "NovaOffice.File"; Tasks: assoc
Root: HKA; Subkey: "Software\NovaOffice\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pptx"; ValueData: "NovaOffice.File"; Tasks: assoc
Root: HKA; Subkey: "Software\NovaOffice\Capabilities\FileAssociations"; ValueType: string; ValueName: ".docx"; ValueData: "NovaOffice.File"; Tasks: assoc
Root: HKA; Subkey: "Software\NovaOffice\Capabilities\FileAssociations"; ValueType: string; ValueName: ".txt"; ValueData: "NovaOffice.File"; Tasks: assoc
Root: HKA; Subkey: "Software\NovaOffice\Capabilities\FileAssociations"; ValueType: string; ValueName: ".md"; ValueData: "NovaOffice.File"; Tasks: assoc
Root: HKA; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "NovaOffice"; ValueData: "Software\NovaOffice\Capabilities"; Flags: uninsdeletevalue; Tasks: assoc

[Run]
Filename: "ms-settings:defaultapps"; Description: "Открыть настройки Windows, чтобы выбрать Nova Office по умолчанию"; Flags: shellexec postinstall skipifsilent unchecked; Tasks: assoc
Filename: "{app}\{#Exe}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent
