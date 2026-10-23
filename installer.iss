; Inno Setup Script for FilePie
#define MyAppName "FilePie"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "OswanYunus"
#define MyAppURL "https://github.com/OswanYunus/filepie"
#define MyAppExeName "FilePie.exe"

[Setup]
AppId={{94C012A3-B75F-4820-9DA2-87B75F256B0E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=FilePie_Setup_v1.0.0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Start FilePie automatically on Windows login"; GroupDescription: "Windows Integration:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "blender_export.py"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

; Register Explorer context menu directly during installation
[Registry]
Root: HKCU; Subkey: "Software\Classes\*\shell\FilePie"; ValueType: string; ValueData: "Convert with FilePie 🥧"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\FilePie"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#MyAppExeName}"",0"
Root: HKCU; Subkey: "Software\Classes\*\shell\FilePie\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" --convert ""%V"""

Root: HKCU; Subkey: "Software\Classes\Directory\shell\FilePie"; ValueType: string; ValueData: "Convert with FilePie 🥧"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Directory\shell\FilePie"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#MyAppExeName}"",0"
Root: HKCU; Subkey: "Software\Classes\Directory\shell\FilePie\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" --convert ""%V"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
