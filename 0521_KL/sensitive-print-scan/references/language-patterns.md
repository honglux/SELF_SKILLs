# 各语言打印/日志/写文件函数模式参考

本文档列出各主流编程语言中所有可能导致敏感信息泄露的输出函数。子 agent 在测试文件时参考对应语言的模式。

---

## ArkTS (HarmonyOS)

### 日志打印函数
```
hilog.debug(domain, tag, format, ...args)
hilog.info(domain, tag, format, ...args)
hilog.warn(domain, tag, format, ...args)
hilog.error(domain, tag, format, ...args)
hilog.fatal(domain, tag, format, ...args)
hilog.isLoggable(domain, tag, level)
hilog.setMinLogLevel(level)
```

### 自定义 Logger 封装（常见模式）
```
Logger.debug/info/warn/error/fatal(message, ...args)
LogUtil.d/i/w/e(message, ...)
```

### Console 调试
```
console.log / console.info / console.warn / console.error
console.debug / console.dir / console.table / console.trace
console.assert / console.count / console.time / console.timeEnd
console.group / console.groupCollapsed / console.groupEnd
```

### 文件写入
```
fs.writeSync(fd, buffer, options?)
fs.write(fd, buffer, options?)
fs.openSync(path, mode)           // 配合 writeSync
Stream.writeSync / Stream.write   // 流式写入
Stream.flushSync / Stream.flush   // 刷新到磁盘
fs.createStreamSync / fs.createStream
fs.copyFileSync / fs.copyFile
```

### 首选项/数据库写入
```
preferences.put(key, value)       // @ohos.data.preferences
preferences.putSync(key, value)
preferences.flush()               // 持久化到磁盘
relationalStore.insert/update/delete/executeSql
distributedKVStore.put/delete
```

### 脱敏标识
```
%{public}s  — 明文输出（敏感数据应避免）
%{private}s — 脱敏输出（敏感数据应使用）
```

---

## JavaScript / TypeScript（浏览器/Node.js）

### Console 打印
```
console.log / console.info / console.warn / console.error
console.debug / console.dir / console.dirxml / console.table
console.trace / console.assert / console.count
console.time / console.timeEnd / console.timeLog
console.group / console.groupCollapsed / console.groupEnd
console.clear / console.profile / console.profileEnd
```

### 浏览器存储（落盘）
```
localStorage.setItem(key, value)
sessionStorage.setItem(key, value)
document.cookie = "key=value;..."
IndexedDB: IDBObjectStore.put / IDBObjectStore.add
Cache API: cache.put(request, response)
```

### 文件下载/保存（浏览器）
```
new Blob([data], {type}) + URL.createObjectURL + <a download>
window.showSaveFilePicker() + FileSystemWritableFileStream.write()
FileSaver.saveAs(blob, filename)
JSZip.file + zip.generateAsync + saveAs
```

### Node.js 文件写入
```
fs.writeFile / fs.writeFileSync
fs.appendFile / fs.appendFileSync
fs.createWriteStream / stream.write
fs.write / fs.writeSync
fs.promises.writeFile / fs.promises.appendFile
```

### 第三方日志库
```
winston.info / winston.error / winston.debug
pino.info / pino.error
bunyan.info / bunyan.error
loglevel.info / loglevel.warn
```

---

## Vue.js（.vue 单文件组件）

### 模板内（重点关注）
```vue
{{ password }} {{ token }} {{ secret }}
<!-- 模板插值直接渲染敏感数据到 DOM -->
```

### Script 内
```
console.log / console.error / console.warn
localStorage.setItem / sessionStorage.setItem
this.$data / this.$store (DevTools 暴露)
```

### Pinia/Vuex 持久化（自动落盘）
```
pinia-plugin-persistedstate → 自动写 localStorage
vuex-persistedstate → 自动写 localStorage/sessionStorage
vue3-persist-storages → 自动写 localStorage/IndexedDB/Cookies
```

### Bridge/API 调用日志
```
bridge.invoke(method, params)  // params 可能含密码
JSON.stringify(response)       // 打印完整响应体
```

---

## Java / Kotlin

### 日志框架
```
// java.util.logging
Logger.info / Logger.warning / Logger.severe / Logger.fine / Logger.finest

// SLF4J / Logback / Log4j
log.debug / log.info / log.warn / log.error / log.trace
logger.debug("message {}", sensitiveVar)

// Android Log
Log.d / Log.i / Log.w / Log.e / Log.v / Log.wtf
```

### 输出流
```
System.out.println / System.out.print / System.out.printf
System.err.println / System.err.print
```

### 文件写入
```
FileWriter.write / FileWriter.append
BufferedWriter.write
Files.write / Files.writeString
FileOutputStream.write
PrintWriter.write / PrintWriter.print / PrintWriter.println
ObjectOutputStream.writeObject
```

### 数据库/配置存储
```
SharedPreferences.edit().putString().apply()/commit()  // Android
SQLiteDatabase.insert / update
Room DAO @Insert / @Update
```

### 脱敏标识（常见）
```
%mask% 或自定义 MaskingConverter
```

---

## Python

### 日志模块
```
logging.debug / logging.info / logging.warning / logging.warn
logging.error / logging.critical / logging.exception
logging.log(level, msg)
logger.debug / logger.info / logger.warning
```

### Print 函数
```
print() / print(value, file=f)
pprint.pprint / pprint.pformat
sys.stdout.write / sys.stderr.write
```

### 文件写入
```
open(file, 'w').write / open(file, 'a').write
file.write / file.writelines
json.dump / json.dumps  → 配合 print/log 时
pickle.dump / pickle.dumps
csv.writer.writerow / csv.DictWriter.writeheader
shutil.copy / shutil.copy2 / shutil.copytree
pathlib.Path.write_text / pathlib.Path.write_bytes
```

### 数据库
```
sqlite3.Connection.execute("INSERT/UPDATE...")
cursor.execute / cursor.executemany
SQLAlchemy session.add / session.commit
Django Model.objects.create / Model.save()
```

---

## Go

### 日志
```
log.Print / log.Printf / log.Println
log.Fatal / log.Fatalf / log.Fatalln
log.Panic / log.Panicf / log.Panicln
slog.Info / slog.Warn / slog.Error / slog.Debug
logrus.Info / logrus.Warn / logrus.Error / logrus.Debug
zap.Info / zap.Warn / zap.Error / zap.Debug
zerolog.Info / zerolog.Warn / zerolog.Error
```

### 输出
```
fmt.Print / fmt.Printf / fmt.Println / fmt.Sprint / fmt.Sprintf
fmt.Fprint / fmt.Fprintf / fmt.Fprintln
os.Stdout.Write / os.Stderr.Write
```

### 文件写入
```
os.WriteFile / os.Create
file.Write / file.WriteString / file.WriteAt
bufio.Writer.Write / bufio.Writer.WriteString
io.Copy / io.WriteString
json.NewEncoder(w).Encode  → 配合输出流时
ioutil.WriteFile (deprecated)
```

### 数据库/配置
```
database/sql: db.Exec("INSERT/UPDATE...")
gorm: db.Create / db.Save / db.Update
viper.WriteConfig / viper.WriteConfigAs
```

---

## C / C++

### 输出
```
printf / fprintf / sprintf / snprintf / asprintf
puts / fputs / putchar / fputc
std::cout << / std::cerr << / std::clog <<
QDebug() << (Qt)
```

### 日志
```
syslog / openlog / vsyslog
__android_log_print (Android NDK)
spdlog::info / spdlog::warn / spdlog::error
glog(INFO) / glog(WARNING) / glog(ERROR)
BOOST_LOG_TRIVIAL(info) / BOOST_LOG_TRIVIAL(error)
```

### 文件写入
```
fopen + fwrite / fputs / fprintf
open + write
std::ofstream << / std::ofstream.write
QFile::write / QTextStream << (Qt)
fstream.write / fstream <<
```

---

## C# / .NET

### 日志
```
// Microsoft.Extensions.Logging
ILogger.LogInformation / ILogger.LogWarning / ILogger.LogError
ILogger.LogDebug / ILogger.LogCritical / ILogger.LogTrace

// NLog / Serilog / log4net
Log.Info / Log.Warn / Log.Error / Log.Debug
```

### 输出
```
Console.Write / Console.WriteLine
Console.Error.Write / Console.Error.WriteLine
Debug.Write / Debug.WriteLine
Trace.Write / Trace.WriteLine
System.Diagnostics.Debug.Print
```

### 文件写入
```
File.WriteAllText / File.WriteAllBytes / File.WriteAllLines
File.AppendAllText / File.AppendAllLines
StreamWriter.Write / StreamWriter.WriteLine
FileStream.Write / BinaryWriter.Write
```

### 数据库
```
SqlCommand.ExecuteNonQuery("INSERT/UPDATE...")
Entity Framework: DbContext.SaveChanges / DbSet.Add / DbSet.Update
```

---

## Swift

### 日志
```
print() / debugPrint() / dump()
NSLog()
os_log / os_log_info / os_log_debug / os_log_error
Logger.log / Logger.info / Logger.warning / Logger.error (OSLog)
```

### 文件写入
```
Data.write(to:) / String.write(to:atomically:encoding:)
FileHandle.write / OutputStream.write
FileManager.createFile
```

---

## PHP

### 输出/日志
```
echo / print / printf / var_dump / print_r / var_export
error_log()
Monolog: $logger->info / $logger->warning / $logger->error
```

### 文件写入
```
file_put_contents / fwrite / fputs / fputcsv
file_put_contents(..., FILE_APPEND)
```

---

## Ruby

### 输出/日志
```
puts / print / printf / p / pp / ap
Rails.logger.info / Rails.logger.warn / Rails.logger.error
Logger.new.info / Logger.new.warn / Logger.new.error
```

### 文件写入
```
File.write / File.open("w").write
IO.write / IO.binwrite
File.open("a") { |f| f.write }
```

---

## 敏感变量关键词（跨语言通用）

在追溯变量来源时，重点关注以下命名模式：

### P0 级别关键词
密码类: `password`, `pwd`, `pass`, `passwd`, `passphrase`
密钥类: `secret`, `secretKey`, `secret_key`, `privateKey`, `private_key`, `apiKey`, `api_key`, `apikey`, `masterKey`, `master_key`
Token类: `token`, `accessToken`, `access_token`, `refreshToken`, `refresh_token`, `bearerToken`, `authToken`, `auth_token`
会话类: `sessionId`, `session_id`, `jsessionid`, `sessionKey`, `session_key`
凭据类: `credential`, `signature`, `authorization`, `wwwAuthenticate`
Cookie类: `cookie`, `setCookie`, `set_cookie`

### P1 级别关键词
加密类: `encrypted`, `encrypt`, `cipher`, `ciphertext`, `cipher_text`
认证类: `nonce`, `cnonce`, `realm`, `response` (仅当为认证响应时), `opaque`
摘要类: `hmac`, `hash`, `digest`, `checksum`
随机数: `random`, `nonce`, `iv`, `salt`
MAC/SN类: `mac`, `macAddress`, `mac_address`, `serial`, `sn`, `serialNumber`
证书类: `cert`, `certificate`, `publicKey`, `public_key`, `ssl`, `tls`

### P2 级别关键词
IP类: `ip`, `ipv4`, `ipv6`, `localIp`, `targetIp`, `srcIp`, `dstIp`, `host`, `gateway`, `netmask`, `subnet`
用户类: `username`, `user`, `account`, `email`, `phone`, `mobile`, `nickname`
设备类: `deviceId`, `deviceName`, `device_name`, `cameraCode`, `camera_code`, `channel`
配置类: `config` (仅当 JSON 序列化后打印时)

---

## 通用注意事项

1. **JSON.stringify 及其等价物**：任何将对象序列化为 JSON 字符串并打印/写入的操作都是高风险点
2. **模板字符串/字符串插值**：`` `password=${pwd}` `` 或 `f"password={pwd}"` 直接嵌入敏感值
3. **异常堆栈打印**：`e.printStackTrace()` / `traceback.print_exc()` 可能泄露局部变量值
4. **HTTP 请求日志**：打印完整 request/response 对象（含 headers）
5. **第三方库日志级别**：`DEBUG` 或 `TRACE` 级别可能打印完整请求/响应体
