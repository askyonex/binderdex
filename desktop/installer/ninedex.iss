; Inno-Setup-Skript fuer den Windows-Installer von Ninedex.
; Voraussetzung: PyInstaller-Ergebnis in dist\Ninedex\ und Symbol in desktop\build\icon.ico
; Aufruf aus dem Repo-Ordner:
;   iscc /DMyAppVersion=1.0.0 desktop\installer\ninedex.iss
; Ergebnis: dist\installer\Ninedex-Setup-1.0.0.exe

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppName "Ninedex"
#define MyAppExe "Ninedex.exe"
#define MyAppPublisher "askyonex"
#define MyAppURL "https://github.com/askyonex/ninedex"
#define Root "..\.."

[Setup]
; Die AppId nie aendern, sonst erkennt Windows Updates nicht als dieselbe App
AppId={{03FE21B1-FEAD-40CB-9DCB-6C5358EF37B4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Standard: Installation nur fuer den eigenen Benutzer, ohne Administratorrechte.
; Im ersten Dialog kann man "fuer alle Benutzer" waehlen.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#Root}\dist\installer
OutputBaseFilename=Ninedex-Setup-{#MyAppVersion}
SetupIconFile={#Root}\desktop\build\icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
LicenseFile={#Root}\LICENSE
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
german.NoWebView2=Ninedex braucht die Microsoft Edge WebView2 Runtime. Sie ist unter Windows 11 und aktuellem Windows 10 normalerweise schon vorhanden, hier aber nicht gefunden worden.%n%nSoll die Download-Seite von Microsoft geöffnet werden? Installiere dort die "Evergreen Bootstrapper"-Version und starte Ninedex danach.
english.NoWebView2=Ninedex needs the Microsoft Edge WebView2 Runtime. It usually ships with Windows 11 and current Windows 10, but it was not found here.%n%nOpen Microsoft's download page now? Install the "Evergreen Bootstrapper" there, then start Ninedex.
spanish.NoWebView2=Ninedex necesita Microsoft Edge WebView2 Runtime. Normalmente ya viene con Windows 11 y con Windows 10 actualizado, pero aquí no se ha encontrado.%n%n¿Abrir ahora la página de descarga de Microsoft? Instala allí el "Evergreen Bootstrapper" y después inicia Ninedex.
german.KeepData=Deine Sammlung (Datenbank und Einstellungen) liegt noch in:%n%1%n%nSoll sie BEHALTEN werden? (Empfohlen, z. B. für eine Neuinstallation.)%n%nJa = behalten, Nein = endgültig löschen
english.KeepData=Your collection (database and settings) is still stored in:%n%1%n%nKeep it? (Recommended, e.g. for a reinstall.)%n%nYes = keep, No = delete permanently
spanish.KeepData=Tu colección (base de datos y ajustes) sigue guardada en:%n%1%n%n¿CONSERVARLA? (Recomendado, p. ej. para reinstalar.)%n%nSí = conservar, No = borrar definitivamente
german.LangTitle=Sprachen
english.LangTitle=Languages
spanish.LangTitle=Idiomas
german.LangDesc=In welchen Sprachen soll Ninedex verfügbar sein?
english.LangDesc=Which languages should Ninedex be available in?
spanish.LangDesc=¿En qué idiomas debe estar disponible Ninedex?
german.LangSub=Oberfläche und Pokédex (Pokémon-Namen und Einträge) erscheinen in der gewählten Sprache. Du kannst mehrere auswählen und in der App jederzeit zwischen ihnen wechseln (Einstellungen > Sprache).
english.LangSub=The interface and the Pokédex (Pokémon names and entries) appear in the selected language. You can select several and switch between them in the app at any time (Settings > Language).
spanish.LangSub=La interfaz y la Pokédex (nombres y entradas de los Pokémon) aparecen en el idioma elegido. Puedes elegir varios y cambiar entre ellos en la app cuando quieras (Ajustes > Idioma).
german.LangNone=Bitte mindestens eine Sprache auswählen.
english.LangNone=Please select at least one language.
spanish.LangNone=Elige al menos un idioma.
german.DefTitle=Startsprache
english.DefTitle=Start language
spanish.DefTitle=Idioma de inicio
german.DefDesc=In welcher Sprache soll Ninedex starten?
english.DefDesc=Which language should Ninedex start in?
spanish.DefDesc=¿En qué idioma debe iniciarse Ninedex?
german.DefSub=Die anderen gewählten Sprachen stehen in der App unter Einstellungen > Sprache zur Auswahl.
english.DefSub=The other selected languages are available in the app under Settings > Language.
spanish.DefSub=Los demás idiomas elegidos están disponibles en la app en Ajustes > Idioma.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#Root}\dist\Ninedex\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Alte Programmdateien bei Updates entfernen (die Sammlung liegt woanders und bleibt)
Type: filesandordirs; Name: "{app}\_internal"
; Reste vom frueheren Namen BinderDex (gleiche AppId, Update laeuft im alten Programmordner)
Type: files; Name: "{app}\BinderDex.exe"
Type: files; Name: "{app}\binderdex.ini"
Type: files; Name: "{autoprograms}\BinderDex.lnk"
Type: files; Name: "{autodesktop}\BinderDex.lnk"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[UninstallDelete]
Type: files; Name: "{app}\ninedex.ini"

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
; Update aus der App heraus (still, mit /update=1): danach Ninedex wieder starten
Filename: "{app}\{#MyAppExe}"; Flags: nowait; Check: IsAppUpdate

[Code]
const
  WebView2Key = 'Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  NLANG = 3;

var
  LangPage, DefPage: TInputOptionWizardPage;
  PrevLangs: String;
  DefCodes: array of String;

function LangCode(i: Integer): String;
begin
  case i of
    0: Result := 'de';
    1: Result := 'en';
  else
    Result := 'es';
  end;
end;

function LangName(i: Integer): String;
begin
  case i of
    0: Result := 'Deutsch';
    1: Result := 'English';
  else
    Result := 'Español';
  end;
end;

function SetupLangCode(): String;
begin
  if ActiveLanguage = 'german' then Result := 'de'
  else if ActiveLanguage = 'spanish' then Result := 'es'
  else Result := 'en';
end;

function SelCount(): Integer;
var
  i: Integer;
begin
  Result := 0;
  for i := 0 to NLANG - 1 do
    if LangPage.Values[i] then Result := Result + 1;
end;

{ Seite mit Mehrfachauswahl der Sprachen; bei einem Update wird die bisherige Auswahl vorgeschlagen }
procedure InitializeWizard();
var
  i: Integer;
  prev: String;
begin
  LangPage := CreateInputOptionPage(wpSelectTasks, CustomMessage('LangTitle'), CustomMessage('LangDesc'), CustomMessage('LangSub'), False, False);
  for i := 0 to NLANG - 1 do
    LangPage.Add(LangName(i));
  prev := '';
  if WizardForm.PrevAppDir <> '' then
    prev := GetIniString('ui', 'languages', '', AddBackslash(WizardForm.PrevAppDir) + 'ninedex.ini');
  if (prev = '') and (WizardForm.PrevAppDir <> '') then
    prev := GetIniString('ui', 'languages', '', AddBackslash(WizardForm.PrevAppDir) + 'binderdex.ini');
  PrevLangs := prev;
  for i := 0 to NLANG - 1 do
    if prev <> '' then
      LangPage.Values[i] := Pos(LangCode(i), prev) > 0
    else
      LangPage.Values[i] := LangCode(i) = SetupLangCode();
  DefPage := CreateInputOptionPage(LangPage.ID, CustomMessage('DefTitle'), CustomMessage('DefDesc'), CustomMessage('DefSub'), True, False);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = LangPage.ID) and (SelCount() = 0) then
  begin
    MsgBox(CustomMessage('LangNone'), mbError, MB_OK);
    Result := False;
  end;
end;

{ Startsprache nur fragen, wenn mehr als eine Sprache gewaehlt ist }
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (DefPage <> nil) and (PageID = DefPage.ID) and (SelCount() < 2);
end;

procedure CurPageChanged(CurPageID: Integer);
var
  i, n: Integer;
begin
  if CurPageID = DefPage.ID then
  begin
    DefPage.CheckListBox.Items.Clear;
    SetArrayLength(DefCodes, 0);
    n := 0;
    for i := 0 to NLANG - 1 do
      if LangPage.Values[i] then
      begin
        DefPage.Add(LangName(i));
        SetArrayLength(DefCodes, n + 1);
        DefCodes[n] := LangCode(i);
        n := n + 1;
      end;
    DefPage.SelectedValueIndex := 0;
    for i := 0 to n - 1 do
      if DefCodes[i] = SetupLangCode() then DefPage.SelectedValueIndex := i;
  end;
end;

{ z. B. "en,de,es": die erste ist die Startsprache }
{ Ninedex hat das Update selbst gestartet (Parameter /update=1) }
function IsAppUpdate(): Boolean;
begin
  Result := ExpandConstant('{param:update|0}') = '1';
end;

function LangList(): String;
var
  i: Integer;
  def: String;
begin
  { Stilles Update: bisherige Auswahl samt Reihenfolge (= Startsprache) unveraendert uebernehmen }
  if WizardSilent() and (PrevLangs <> '') then
  begin
    Result := PrevLangs;
    exit;
  end;
  def := '';
  if (SelCount() >= 2) and (GetArrayLength(DefCodes) > 0) and (DefPage.SelectedValueIndex >= 0) then
    def := DefCodes[DefPage.SelectedValueIndex];
  if def = '' then
  begin
    if LangPage.Values[0] and (SetupLangCode() = 'de') then def := 'de'
    else if LangPage.Values[1] and (SetupLangCode() = 'en') then def := 'en'
    else if LangPage.Values[2] and (SetupLangCode() = 'es') then def := 'es';
  end;
  if def = '' then
    for i := NLANG - 1 downto 0 do
      if LangPage.Values[i] then def := LangCode(i);
  if def = '' then def := SetupLangCode();
  Result := def;
  for i := 0 to NLANG - 1 do
    if LangPage.Values[i] and (LangCode(i) <> def) then
      Result := Result + ',' + LangCode(i);
end;

function WebView2Present(): Boolean;
var
  v: String;
begin
  Result :=
    (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\' + WebView2Key, 'pv', v) and (v <> '') and (v <> '0.0.0.0')) or
    (RegQueryStringValue(HKLM, 'SOFTWARE\' + WebView2Key, 'pv', v) and (v <> '') and (v <> '0.0.0.0')) or
    (RegQueryStringValue(HKCU, 'Software\' + WebView2Key, 'pv', v) and (v <> '') and (v <> '0.0.0.0'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ErrorCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    { Sprachauswahl fuer den Starter (desktop/ninedex_desktop.py liest sie bei jedem Start) }
    SaveStringToFile(ExpandConstant('{app}\ninedex.ini'), '[ui]' + #13#10 + 'languages=' + LangList() + #13#10, False);
    if (not WebView2Present()) and (not WizardSilent()) then
      if MsgBox(CustomMessage('NoWebView2'), mbConfirmation, MB_YESNO) = IDYES then
        ShellExec('open', 'https://developer.microsoft.com/microsoft-edge/webview2/', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\Ninedex');
    if DirExists(DataDir) and (not UninstallSilent()) then
      if MsgBox(FmtMessage(CustomMessage('KeepData'), [DataDir]), mbConfirmation, MB_YESNO or MB_DEFBUTTON1) = IDNO then
        DelTree(DataDir, True, True, True);
  end;
end;
