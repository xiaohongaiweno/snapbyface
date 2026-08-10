#define MyAppName "SnapByFace"
#ifndef SourceDir
#define SourceDir "..\dist\SnapByFace"
#endif
#ifndef OutputDir
#define OutputDir "..\dist\installers"
#endif
#ifndef AppVersion
#define AppVersion "0.1.0"
#endif

[Setup]
AppId={{9A15BE06-41EC-4117-AD7F-0254A8D1AFB8}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher=SnapByFace
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=SnapByFace-Windows-{#AppVersion}-Setup
SetupIconFile=..\resources\snapbyface.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\SnapByFace.exe

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\SnapByFace.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\SnapByFace.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\SnapByFace.exe"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
