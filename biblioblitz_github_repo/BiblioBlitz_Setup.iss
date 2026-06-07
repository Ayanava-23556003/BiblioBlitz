[Setup]
AppName=BiblioBlitz
AppVersion=4.1
AppPublisher=Ayanava Poddar
AppPublisherURL=https://github.com/Ayanava-23556003/BiblioBlitz
DefaultDirName={autopf}\BiblioBlitz
DefaultGroupName=BiblioBlitz
OutputDir=.
OutputBaseFilename=BiblioBlitz_Setup_v4.1
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\biblioblitz.ico

[Files]
Source: "BiblioBlitz.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "biblioblitz.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\BiblioBlitz"; Filename: "{app}\BiblioBlitz.exe"; IconFilename: "{app}\biblioblitz.ico"
Name: "{autodesktop}\BiblioBlitz"; Filename: "{app}\BiblioBlitz.exe"; IconFilename: "{app}\biblioblitz.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a functional Desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\BiblioBlitz.exe"; Description: "Launch BiblioBlitz Workspace Now"; Flags: nowait postinstall skipifsilent