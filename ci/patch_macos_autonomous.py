from pathlib import Path
import subprocess, sys

root=Path(sys.argv[1] if len(sys.argv)>1 else 'work/MedicalRecord2026')
if not root.exists(): raise SystemExit(f'Source root not found: {root}')
subprocess.run([sys.executable,str(Path(__file__).with_name('patch_personal_internal.py')),str(root)],check=True)

def rw(rel,*pairs):
    p=root/rel; s=p.read_text(encoding='utf-8')
    for a,b in pairs:
        if a not in s:
            print(f'WARN: pattern not found in {rel}: {a[:80]!r}')
        s=s.replace(a,b)
    p.write_text(s,encoding='utf-8')

rw('Directory.Packages.props',
   ('<PackageVersion Include="Microsoft.EntityFrameworkCore.Design" Version="10.0.11" />',
    '<PackageVersion Include="Microsoft.EntityFrameworkCore.Design" Version="10.0.11" />\n    <PackageVersion Include="Microsoft.EntityFrameworkCore.Sqlite" Version="10.0.11" />'))
rw('src/MedicalRecord.Infrastructure/MedicalRecord.Infrastructure.csproj',
   ('<PackageReference Include="Microsoft.EntityFrameworkCore.Design"><PrivateAssets>all</PrivateAssets><IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets></PackageReference>',
    '<PackageReference Include="Microsoft.EntityFrameworkCore.Design"><PrivateAssets>all</PrivateAssets><IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets></PackageReference>\n    <PackageReference Include="Microsoft.EntityFrameworkCore.Sqlite" />'))
rw('src/MedicalRecord.Api/MedicalRecord.Api.csproj',
   ('<PackageReference Include="Npgsql.EntityFrameworkCore.PostgreSQL" />',
    '<PackageReference Include="Npgsql.EntityFrameworkCore.PostgreSQL" />\n    <PackageReference Include="Microsoft.EntityFrameworkCore.Sqlite" />'))

p=root/'src/MedicalRecord.Infrastructure/Persistence/MedicalDbContext.cs'
s=p.read_text(encoding='utf-8')
if 'Microsoft.EntityFrameworkCore.Storage.ValueConversion' not in s:
    s=s.replace('using Microsoft.EntityFrameworkCore;','using Microsoft.EntityFrameworkCore;\nusing Microsoft.EntityFrameworkCore.Storage.ValueConversion;')
needle='''        modelBuilder.Entity<BackupRecord>(e =>\n        {\n            e.ToTable("backup_records"); e.HasKey(x => x.Id); e.Property(x => x.Status).HasMaxLength(32).IsRequired(); e.Property(x => x.BackupType).HasMaxLength(40).IsRequired(); e.Property(x => x.StorageReference).HasMaxLength(600); e.Property(x => x.Sha256).HasMaxLength(64); e.HasIndex(x => x.RequestedAt);\n        });\n'''
insert=needle+'''\n        if (Database.ProviderName == "Microsoft.EntityFrameworkCore.Sqlite")\n        {\n            var converter = new ValueConverter<DateTimeOffset, long>(\n                value => value.UtcDateTime.Ticks,\n                value => new DateTimeOffset(new DateTime(value, DateTimeKind.Utc)));\n            foreach (var entityType in modelBuilder.Model.GetEntityTypes())\n                foreach (var property in entityType.GetProperties().Where(x => x.ClrType == typeof(DateTimeOffset)))\n                    property.SetValueConverter(converter);\n        }\n'''
if 'ProviderName == "Microsoft.EntityFrameworkCore.Sqlite"' not in s:
    if needle not in s: raise SystemExit('Could not patch MedicalDbContext SQLite converter')
    s=s.replace(needle,insert)
p.write_text(s,encoding='utf-8')

p=root/'src/MedicalRecord.Infrastructure/Persistence/DbBootstrapper.cs'
s=p.read_text(encoding='utf-8')
s=s.replace('public static async Task InitializeAsync(MedicalDbContext db, bool development, CancellationToken cancellationToken = default)',
            'public static async Task InitializeAsync(MedicalDbContext db, bool development, bool personalInternal = false, CancellationToken cancellationToken = default)')
s=s.replace('if (development) await db.Database.EnsureCreatedAsync(cancellationToken);\n                else await db.Database.MigrateAsync(cancellationToken);',
            'if (development || personalInternal) await db.Database.EnsureCreatedAsync(cancellationToken);\n                else await db.Database.MigrateAsync(cancellationToken);')
old='''        if (development)\n        {\n            await SeedUsersAsync(db, cancellationToken);\n            await SeedPatientsAsync(db, cancellationToken);\n            await SeedCatalogsAsync(db, cancellationToken);\n            await SeedAppointmentsAsync(db, cancellationToken);\n        }\n        else\n        {\n            await BootstrapProductionAdminAsync(db, cancellationToken);\n        }\n'''
new='''        if (personalInternal)\n        {\n            await SeedPersonalUserAsync(db, cancellationToken);\n            await SeedCatalogsAsync(db, cancellationToken);\n        }\n        else if (development)\n        {\n            await SeedUsersAsync(db, cancellationToken);\n            await SeedPatientsAsync(db, cancellationToken);\n            await SeedCatalogsAsync(db, cancellationToken);\n            await SeedAppointmentsAsync(db, cancellationToken);\n        }\n        else\n        {\n            await BootstrapProductionAdminAsync(db, cancellationToken);\n        }\n'''
if old not in s: raise SystemExit('Could not patch DbBootstrapper mode block')
s=s.replace(old,new)
marker='    private static async Task SeedUsersAsync(MedicalDbContext db, CancellationToken ct)\n'
personal='''    private static async Task SeedPersonalUserAsync(MedicalDbContext db, CancellationToken ct)\n    {\n        var password=Environment.GetEnvironmentVariable("MEDICALRECORD_INTERNAL_PASSWORD");\n        if(string.IsNullOrWhiteSpace(password) || password.Length<24)\n            throw new InvalidOperationException("Personal/Internal local credential is missing or too short.");\n        var userName=Environment.GetEnvironmentVariable("MEDICALRECORD_INTERNAL_USER") ?? "owner";\n        var display=Environment.GetEnvironmentVariable("MEDICALRECORD_INTERNAL_DISPLAY") ?? "Бабак Сергей Львович";\n        var user=await db.Users.SingleOrDefaultAsync(x=>x.UserName==userName,ct);\n        if(user is null)\n        {\n            var c=PasswordHasher.HashPassword(password);\n            db.Users.Add(new AppUser{UserName=userName,DisplayName=display,Role="Admin",PasswordSalt=c.Salt,PasswordHash=c.Hash,IsActive=true});\n        }\n        else\n        {\n            user.DisplayName=display; user.Role="Admin"; user.IsActive=true;\n            if(!PasswordHasher.Verify(password,user.PasswordSalt,user.PasswordHash))\n            {\n                var c=PasswordHasher.HashPassword(password); user.PasswordSalt=c.Salt; user.PasswordHash=c.Hash;\n            }\n        }\n        await db.SaveChangesAsync(ct);\n    }\n\n'''
if 'SeedPersonalUserAsync' not in s[s.find(marker):]:
    s=s.replace(marker,personal+marker)
p.write_text(s,encoding='utf-8')

(root/'src/MedicalRecord.Api/Program.cs').write_text(r'''using System.Diagnostics;
using MedicalRecord.Api.Endpoints;
using MedicalRecord.Api.Support;
using MedicalRecord.Contracts;
using MedicalRecord.Domain.Entities;
using MedicalRecord.Infrastructure.Persistence;
using MedicalRecord.Infrastructure.Cryptography;
using MedicalRecord.Infrastructure.Security;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);
var provider = Environment.GetEnvironmentVariable("MEDICALRECORD_DB_PROVIDER")
               ?? builder.Configuration["Database:Provider"]
               ?? "PostgreSQL";
var personalInternal = provider.Equals("Sqlite", StringComparison.OrdinalIgnoreCase);
var databaseLabel = personalInternal ? "SQLite" : "PostgreSQL";
if (personalInternal)
{
    var dbPath = Environment.GetEnvironmentVariable("MEDICALRECORD_SQLITE_PATH");
    if (string.IsNullOrWhiteSpace(dbPath))
        throw new InvalidOperationException("MEDICALRECORD_SQLITE_PATH is required for Personal/Internal SQLite mode.");
    var directory = Path.GetDirectoryName(dbPath);
    if (!string.IsNullOrWhiteSpace(directory)) Directory.CreateDirectory(directory);
    builder.Services.AddDbContext<MedicalDbContext>(o => o.UseSqlite($"Data Source={dbPath};Cache=Shared;Pooling=True"));
}
else
{
    var connectionString = builder.Configuration.GetConnectionString("MedicalDb")
                           ?? throw new InvalidOperationException("Connection string 'MedicalDb' is not configured.");
    builder.Services.AddDbContext<MedicalDbContext>(o => o.UseNpgsql(connectionString));
}
builder.Services.AddSingleton<IDigitalSignatureProvider, ManagedCmsVerificationProvider>();

var app = builder.Build();
var productionRelease = builder.Configuration.GetValue("Release:ProductionRelease", false);
if (!personalInternal && !app.Environment.IsDevelopment() && !productionRelease)
    throw new InvalidOperationException("Production startup is fail-closed. Set Release:ProductionRelease=true only for an approved release configuration.");
await using (var scope=app.Services.CreateAsyncScope())
{
    var db=scope.ServiceProvider.GetRequiredService<MedicalDbContext>();
    await DbBootstrapper.InitializeAsync(db, app.Environment.IsDevelopment(), personalInternal);
}
if (!personalInternal && !app.Environment.IsDevelopment() && builder.Configuration.GetValue("Release:RequireHttps", true))
    app.UseHttpsRedirection();

app.Use(async (context,next) =>
{
    if (ApiSecurity.IsAnonymousPath(context.Request.Path)) { await next(); return; }
    var header=context.Request.Headers.Authorization.ToString();
    if (!header.StartsWith("Bearer ",StringComparison.OrdinalIgnoreCase)) { context.Response.StatusCode=401; await context.Response.WriteAsJsonAsync(new { message="Требуется авторизация." }); return; }
    var hash=PasswordHasher.HashToken(header[7..].Trim());
    var db=context.RequestServices.GetRequiredService<MedicalDbContext>();
    var session=await db.UserSessions.Include(x=>x.User).SingleOrDefaultAsync(x=>x.TokenHash==hash && !x.IsRevoked && x.ExpiresAt>DateTimeOffset.UtcNow);
    if (session?.User is null || !session.User.IsActive) { context.Response.StatusCode=401; await context.Response.WriteAsJsonAsync(new { message="Сеанс истёк или отозван." }); return; }
    context.Items["CurrentUser"]=session.User; context.Items["CurrentSession"]=session; await next();
});

app.MapGet("/api/health", async (MedicalDbContext db,CancellationToken ct) =>
{
    var ok=await db.Database.CanConnectAsync(ct); return Results.Ok(new ApiHealthDto(ok?"ok":"degraded",ok,databaseLabel,DateTimeOffset.UtcNow));
});
app.MapAuthEndpoints();
app.MapPatientEndpoints();
app.MapEncounterEndpoints();
app.MapDiagnosticEndpoints();
app.MapPapEndpoints();
app.MapDocumentEndpoints();
app.MapScheduleEndpoints();
app.MapCatalogEndpoints();
app.MapGlobalDocumentEndpoints();
app.MapBackupEndpoints();
app.MapSystemEndpoints();

if (personalInternal && int.TryParse(Environment.GetEnvironmentVariable("MEDICALRECORD_PARENT_PID"), out var parentPid))
{
    _ = Task.Run(async () =>
    {
        while (!app.Lifetime.ApplicationStopping.IsCancellationRequested)
        {
            try { using var parent=Process.GetProcessById(parentPid); if(parent.HasExited) break; }
            catch { break; }
            await Task.Delay(1000);
        }
        app.Lifetime.StopApplication();
    });
}

app.Run();
''',encoding='utf-8')

rw('src/MedicalRecord.Api/Endpoints/SystemEndpoints.cs',
   ('cfg.GetValue("Release:ProductionRelease",false),"PostgreSQL","CMS boundary / qualified provider required"',
    'cfg.GetValue("Release:ProductionRelease",false),(Environment.GetEnvironmentVariable("MEDICALRECORD_DB_PROVIDER")??"PostgreSQL"),"CMS boundary / qualified provider required"'),
   ('"1.0.0-internal"','"1.1.0-internal-autonomous"'))

services=root/'src/MedicalRecord.Desktop/Services'
services.mkdir(parents=True,exist_ok=True)
(services/'LocalServerManager.cs').write_text(r'''using System.Diagnostics;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text.Json;
using MedicalRecord.Contracts;

namespace MedicalRecord.Desktop.Services;

public sealed record InternalCredentials(string UserName, string Password);

public static class LocalServerManager
{
    public const string ApiUrl = "http://127.0.0.1:5186/";
    private static readonly SemaphoreSlim Gate = new(1,1);
    private static Process? _serverProcess;
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented=true, PropertyNameCaseInsensitive=true };

    public static string DataDirectory => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),"Library","Application Support","MedicalRecord2026");
    public static string DatabasePath => Path.Combine(DataDirectory,"medicalrecord.db");
    public static string CredentialsPath => Path.Combine(DataDirectory,"internal.credentials.json");
    private static string MarkerPath => Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","Resources","personal-internal.autonomous"));
    private static string ServerDirectory => Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","Resources","Server"));
    private static string ServerExecutable => Path.Combine(ServerDirectory,"MedicalRecord.Api");
    public static bool IsAutonomous => OperatingSystem.IsMacOS() && File.Exists(MarkerPath);

    public static InternalCredentials GetCredentials()
    {
        Directory.CreateDirectory(DataDirectory);
        if (File.Exists(CredentialsPath))
        {
            var current=JsonSerializer.Deserialize<InternalCredentials>(File.ReadAllText(CredentialsPath),JsonOptions);
            if(current is not null && !string.IsNullOrWhiteSpace(current.UserName) && current.Password.Length>=24) return current;
        }
        var created=new InternalCredentials("owner",Convert.ToHexString(RandomNumberGenerator.GetBytes(32)));
        File.WriteAllText(CredentialsPath,JsonSerializer.Serialize(created,JsonOptions));
        if (OperatingSystem.IsMacOS())
            File.SetUnixFileMode(CredentialsPath,UnixFileMode.UserRead|UnixFileMode.UserWrite);
        return created;
    }

    public static async Task EnsureStartedAsync(CancellationToken ct=default)
    {
        if(!IsAutonomous) return;
        await Gate.WaitAsync(ct);
        try
        {
            if(await IsHealthyAsync(ct)) return;
            if(!File.Exists(ServerExecutable)) throw new FileNotFoundException("Встроенный локальный API не найден.",ServerExecutable);
            Directory.CreateDirectory(DataDirectory);
            var credentials=GetCredentials();
            var psi=new ProcessStartInfo(ServerExecutable)
            {
                WorkingDirectory=ServerDirectory,
                UseShellExecute=false,
                CreateNoWindow=true
            };
            psi.Environment["ASPNETCORE_URLS"]=ApiUrl;
            psi.Environment["ASPNETCORE_ENVIRONMENT"]="Development";
            psi.Environment["MEDICALRECORD_DB_PROVIDER"]="Sqlite";
            psi.Environment["MEDICALRECORD_SQLITE_PATH"]=DatabasePath;
            psi.Environment["MEDICALRECORD_INTERNAL_USER"]=credentials.UserName;
            psi.Environment["MEDICALRECORD_INTERNAL_PASSWORD"]=credentials.Password;
            psi.Environment["MEDICALRECORD_INTERNAL_DISPLAY"]="Бабак Сергей Львович";
            psi.Environment["MEDICALRECORD_PARENT_PID"]=Environment.ProcessId.ToString();
            _serverProcess=Process.Start(psi) ?? throw new InvalidOperationException("Не удалось запустить встроенный локальный API.");
            for(var i=0;i<80;i++)
            {
                ct.ThrowIfCancellationRequested();
                if(_serverProcess.HasExited) throw new InvalidOperationException($"Локальный API завершился с кодом {_serverProcess.ExitCode}.");
                if(await IsHealthyAsync(ct)) return;
                await Task.Delay(250,ct);
            }
            throw new TimeoutException("Локальный API не стал готов за 20 секунд.");
        }
        finally { Gate.Release(); }
    }

    public static async Task<ApiHealthDto?> GetHealthAsync(CancellationToken ct=default)
    {
        using var http=new HttpClient{BaseAddress=new Uri(ApiUrl),Timeout=TimeSpan.FromSeconds(2)};
        return await http.GetFromJsonAsync<ApiHealthDto>("api/health",ct);
    }

    private static async Task<bool> IsHealthyAsync(CancellationToken ct)
    {
        try
        {
            var health=await GetHealthAsync(ct);
            return health?.DatabaseConnected==true && string.Equals(health.Database,"SQLite",StringComparison.OrdinalIgnoreCase);
        }
        catch { return false; }
    }

    public static void Shutdown()
    {
        var process=_serverProcess;
        _serverProcess=null;
        if(process is null) return;
        try
        {
            if(!process.HasExited)
            {
                using var term=Process.Start(new ProcessStartInfo("/bin/kill",$"-TERM {process.Id}"){UseShellExecute=false,CreateNoWindow=true});
                term?.WaitForExit(1000);
                if(!process.WaitForExit(4000)) process.Kill(entireProcessTree:true);
            }
        }
        catch
        {
            try { if(!process.HasExited) process.Kill(entireProcessTree:true); } catch { }
        }
        finally { process.Dispose(); }
    }
}
''',encoding='utf-8')

(root/'src/MedicalRecord.Desktop/Program.cs').write_text(r'''using System.Runtime.InteropServices;
using System.Text.Json;
using Avalonia;
using MedicalRecord.Desktop.Services;

namespace MedicalRecord.Desktop;

internal static class Program
{
    [STAThread]
    public static void Main(string[] args)
    {
        if (args.Any(a => string.Equals(a, "--self-test", StringComparison.OrdinalIgnoreCase)))
        {
            Environment.ExitCode = RunSelfTest();
            return;
        }
        try
        {
            if(LocalServerManager.IsAutonomous) LocalServerManager.EnsureStartedAsync().GetAwaiter().GetResult();
            BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
        }
        finally { if(LocalServerManager.IsAutonomous) LocalServerManager.Shutdown(); }
    }

    private static int RunSelfTest()
    {
        try
        {
            var baseDir = AppContext.BaseDirectory;
            var cfg = Path.Combine(baseDir, "medicalrecord.client.json");
            if (!File.Exists(cfg)) throw new FileNotFoundException("Packaged client configuration is missing.", cfg);
            using var doc = JsonDocument.Parse(File.ReadAllText(cfg));
            if (!doc.RootElement.TryGetProperty("ApiUrl", out var api) || string.IsNullOrWhiteSpace(api.GetString()))
                throw new InvalidDataException("medicalrecord.client.json does not contain ApiUrl.");
            var exe = Environment.ProcessPath;
            if (string.IsNullOrWhiteSpace(exe) || !File.Exists(exe)) throw new FileNotFoundException("Running app host cannot be resolved.", exe);

            if(LocalServerManager.IsAutonomous)
            {
                LocalServerManager.EnsureStartedAsync().GetAwaiter().GetResult();
                var health=LocalServerManager.GetHealthAsync().GetAwaiter().GetResult();
                if(health?.DatabaseConnected!=true || !string.Equals(health.Database,"SQLite",StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Autonomous SQLite health check failed.");
                if(!File.Exists(LocalServerManager.DatabasePath)) throw new FileNotFoundException("Autonomous SQLite database was not created.",LocalServerManager.DatabasePath);
                var credentials=LocalServerManager.GetCredentials();
                var client=new MedicalApiClient(new HttpClient{BaseAddress=new Uri(LocalServerManager.ApiUrl)});
                var session=client.LoginAsync(credentials.UserName,credentials.Password).GetAwaiter().GetResult();
                if(session.Role!="Admin") throw new InvalidOperationException("Autonomous owner login did not receive Admin role.");
                Console.WriteLine($"AUTONOMOUS SELF-TEST PASS | Medical Record 2026 | {RuntimeInformation.OSDescription} | {RuntimeInformation.ProcessArchitecture} | API={LocalServerManager.ApiUrl} | DB=SQLite");
            }
            else
            {
                Console.WriteLine($"SELF-TEST PASS | Medical Record 2026 | {RuntimeInformation.OSDescription} | {RuntimeInformation.ProcessArchitecture} | API={api.GetString()}");
            }
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"SELF-TEST FAIL | {ex.GetType().Name}: {ex.Message}");
            return 23;
        }
        finally { if(LocalServerManager.IsAutonomous) LocalServerManager.Shutdown(); }
    }

    public static AppBuilder BuildAvaloniaApp() =>
        AppBuilder.Configure<App>()
            .UsePlatformDetect()
            .LogToTrace();
}
''',encoding='utf-8')

rw('src/MedicalRecord.Desktop/Services/ClientConfiguration.cs',
   ('return cfg with { ApiUrl=ClientConfiguration.Normalize(cfg.ApiUrl), FirstRunCompleted=false };',
    'return cfg with { ApiUrl=ClientConfiguration.Normalize(cfg.ApiUrl) };'))

p=root/'src/MedicalRecord.Desktop/ViewModels/MainWindowViewModel.cs'
s=p.read_text(encoding='utf-8')
s=s.replace('''        var cfg=settings.Load();\n        if(!cfg.FirstRunCompleted) CurrentPage=new SetupViewModel(api,settings,cfg,ShowLoginAsync);\n        else ShowLogin();\n''','''        var cfg=settings.Load();\n        if(LocalServerManager.IsAutonomous)\n        {\n            var login=new LoginViewModel(_api){Status="Локальная база готова. Выполняется безопасный автоматический вход…"};\n            CurrentPage=login; _=AutoLoginAsync(login);\n        }\n        else if(!cfg.FirstRunCompleted) CurrentPage=new SetupViewModel(api,settings,cfg,ShowLoginAsync);\n        else ShowLogin();\n''')
marker='    private void ShowLogin(){var login=new LoginViewModel(_api);login.Authenticated+=OnAuthenticatedAsync;CurrentPage=login;}\n'
auto='''    private async Task AutoLoginAsync(LoginViewModel login)\n    {\n        try\n        {\n            var credentials=LocalServerManager.GetCredentials();\n            var session=await _api.LoginAsync(credentials.UserName,credentials.Password);\n            await OnAuthenticatedAsync(session);\n        }\n        catch(Exception ex)\n        {\n            login.Status=$"Автоматический вход не выполнен: {ex.Message}";\n        }\n    }\n\n'''
if auto.strip() not in s:
    s=s.replace(marker,auto+marker)
p.write_text(s,encoding='utf-8')

rw('src/MedicalRecord.Desktop/ViewModels/LoginViewModel.cs',
   ('PostgreSQL недоступен. Запустите docker compose up -d postgres.','Локальная медицинская база недоступна. Перезапустите приложение.'))
rw('src/MedicalRecord.Desktop/ViewModels/SetupViewModel.cs',
   ('; PostgreSQL доступен.','; база данных доступна.'))

rw('src/MedicalRecord.Desktop/MedicalRecord.Desktop.csproj',('<Version>1.0.0</Version>','<Version>1.1.0</Version>'))
(root/'VERSION').write_text('1.1.0-internal-autonomous\n',encoding='utf-8')
rw('src/MedicalRecord.Desktop/MainWindow.axaml',('Personal/Internal 1.0','Personal/Internal 1.1 · Autonomous'))
rw('src/MedicalRecord.Desktop/Views/DashboardView.axaml',('Personal/Internal 1.0','Personal/Internal 1.1 · Autonomous'))
rw('src/MedicalRecord.Desktop/Views/LoginView.axaml',('Personal/Internal 1.0','Personal/Internal 1.1 · Autonomous'))
rw('src/MedicalRecord.Desktop/Views/DiagnosticStudyEditorView.axaml',('Personal/Internal 1.0','Personal/Internal 1.1 · Autonomous'))
rw('src/MedicalRecord.Desktop/Views/DocumentPreviewView.axaml',('Personal/Internal 1.0','Personal/Internal 1.1 · Autonomous'))
rw('src/MedicalRecord.Api/Endpoints/SystemEndpoints.cs',('"1.0.0-internal"','"1.1.0-internal-autonomous"'))

p=root/'packaging/macos/build-installer.sh'
s=p.read_text(encoding='utf-8')
s=s.replace('VERSION="${VERSION:-1.0.0}"','VERSION="${VERSION:-1.1.0}"')
s=s.replace('PUBLISH="$ROOT/artifacts/publish/$RID"','PUBLISH="$ROOT/artifacts/publish/$RID"\nSERVER_PUBLISH="$ROOT/artifacts/publish/$RID-server"')
s=s.replace('mkdir -p "$PUBLISH" "$OUT"; rm -rf "$PUBLISH" "$APP" "$PKG" "$DMG"; mkdir -p "$PUBLISH" "$OUT"',
'''mkdir -p "$PUBLISH" "$OUT"; rm -rf "$PUBLISH" "$SERVER_PUBLISH" "$APP" "$PKG" "$DMG"; mkdir -p "$PUBLISH" "$SERVER_PUBLISH" "$OUT"''')
s=s.replace('dotnet publish "$ROOT/src/MedicalRecord.Desktop/MedicalRecord.Desktop.csproj" -c Release -r "$RID" --self-contained true -o "$PUBLISH" -p:Version="$VERSION" -p:UseAppHost=true -p:ContinuousIntegrationBuild=true',
'''dotnet publish "$ROOT/src/MedicalRecord.Desktop/MedicalRecord.Desktop.csproj" -c Release -r "$RID" --self-contained true -o "$PUBLISH" -p:Version="$VERSION" -p:UseAppHost=true -p:ContinuousIntegrationBuild=true\ndotnet publish "$ROOT/src/MedicalRecord.Api/MedicalRecord.Api.csproj" -c Release -r "$RID" --self-contained true -o "$SERVER_PUBLISH" -p:Version="$VERSION" -p:UseAppHost=true -p:ContinuousIntegrationBuild=true''')
oldpy="""with open(path,'w',encoding='utf-8') as f: json.dump({'ApiUrl':url,'FirstRunCompleted':False,'OrganizationName':''},f,ensure_ascii=False,indent=2); f.write('\\n')"""
newpy="""with open(path,'w',encoding='utf-8') as f: json.dump({'ApiUrl':'http://127.0.0.1:5186/','FirstRunCompleted':True,'OrganizationName':'Personal/Internal Autonomous'},f,ensure_ascii=False,indent=2); f.write('\\n')"""
s=s.replace(oldpy,newpy)
s=s.replace('mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"; cp -R "$PUBLISH/"* "$APP/Contents/MacOS/"',
'''mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/Server"; cp -R "$PUBLISH/"* "$APP/Contents/MacOS/"; cp -R "$SERVER_PUBLISH/"* "$APP/Contents/Resources/Server/"; touch "$APP/Contents/Resources/personal-internal.autonomous"''')
s=s.replace('chmod +x "$APP/Contents/MacOS/MedicalRecord2026"','chmod +x "$APP/Contents/MacOS/MedicalRecord2026" "$APP/Contents/Resources/Server/MedicalRecord.Api"')
p.write_text(s,encoding='utf-8')

p=root/'packaging/macos/test-installer.sh'
s=p.read_text(encoding='utf-8')
s=s.replace('[[ -x "$APP/Contents/MacOS/MedicalRecord2026" ]] || { echo \'Installed executable missing.\' >&2; exit 31; }\n"$APP/Contents/MacOS/MedicalRecord2026" --self-test',
'''[[ -x "$APP/Contents/MacOS/MedicalRecord2026" ]] || { echo 'Installed executable missing.' >&2; exit 31; }\n[[ -x "$APP/Contents/Resources/Server/MedicalRecord.Api" ]] || { echo 'Embedded local API missing.' >&2; exit 33; }\n"$APP/Contents/MacOS/MedicalRecord2026" --self-test\n[[ -f "$HOME/Library/Application Support/MedicalRecord2026/medicalrecord.db" ]] || { echo 'Autonomous SQLite database missing after self-test.' >&2; exit 34; }''')
s=s.replace('[[ -d "$MOUNT/Medical Record 2026.app" ]] || { hdiutil detach "$MOUNT"; echo \'DMG does not contain app bundle.\' >&2; exit 32; }',
'''[[ -d "$MOUNT/Medical Record 2026.app" ]] || { hdiutil detach "$MOUNT"; echo 'DMG does not contain app bundle.' >&2; exit 32; }\n[[ -x "$MOUNT/Medical Record 2026.app/Contents/Resources/Server/MedicalRecord.Api" ]] || { hdiutil detach "$MOUNT"; echo 'DMG embedded local API missing.' >&2; exit 35; }\n"$MOUNT/Medical Record 2026.app/Contents/MacOS/MedicalRecord2026" --self-test''')
p.write_text(s,encoding='utf-8')

(root/'packaging/AUTONOMOUS_MACOS.ru.md').write_text('''# Medical Record 2026 — Personal/Internal 1.1 Autonomous for macOS\n\nЭта сборка не требует отдельного API, PostgreSQL, Docker или ручного адреса сервера.\n\n- Desktop автоматически запускает встроенный self-contained `MedicalRecord.Api`.\n- API слушает только `http://127.0.0.1:5186/`.\n- Локальная база: `~/Library/Application Support/MedicalRecord2026/medicalrecord.db`.\n- Локальные учётные данные генерируются случайно и хранятся с правами только владельца в `internal.credentials.json`; вход выполняется автоматически.\n- База при первом запуске пустая; добавляются только персональная учётная запись и базовые справочники.\n- Production-режим по-прежнему использует PostgreSQL и не изменён.\n\nCI считается успешным только если установленный `.pkg` и приложение из `.dmg` запускают встроенный API, создают SQLite БД, проходят `/api/health`, выполняют вход владельца и возвращают `AUTONOMOUS SELF-TEST PASS`.\n''',encoding='utf-8')
print('Medical Record 2026 macOS Autonomous 1.1 patch applied')
