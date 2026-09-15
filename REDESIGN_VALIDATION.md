# Radio XP Automator — inventario y validación del rediseño

La pantalla principal conserva el motor y los manejadores de `main.py`. La vista Emisión resume el estado; las vistas secundarias mantienen los controles completos que no caben en la consola compacta.

| Función existente | Ubicación anterior | Manejador o servicio | Nueva ubicación | Comprobación |
|---|---|---|---|---|
| Señal principal | Consola de emisión | `_toggle_signal`, `AudioPassthrough` | Emisión → Volver a cadena; Pautas locales → Consola | Conectado al mismo botón operativo `btn_signal` |
| Pauta local | Consola y reproductor | `_toggle_pauta`, `AudioEngine` | Emisión → Emitir pauta local; Pautas locales → Reproductor | Usa la playlist real; el estado de fila se actualiza desde `track_changed` |
| Play, pausa, parada, anterior, siguiente, seek y volumen | Reproductor | `AudioEngine` y manejadores `_toggle_play_pause`, `_stop_playback` | Pautas locales → Reproductor | Controles originales preservados |
| Cargar, abrir, guardar y eliminar playlist | Toolbar/reproductor | `_add_to_playlist`, `_open_playlist_file`, `_save_playlist_file`, `_remove_from_playlist` | Pautas locales | Acciones visibles y conectadas a los manejadores originales |
| Detector DTMF | Consola/Configuración DTMF | `DTMFDetector`, `_toggle_dtmf` | Emisión → resumen; Reglas DTMF → controles completos | Estado, dispositivos, parámetros y prueba preservados |
| Secuencias DTMF | Configuración DTMF | `_dtmf_seq_play`, `_dtmf_seq_stop`, `_apply_dtmf_params` | Emisión → tabla de reglas; Reglas DTMF → edición | La tabla resumen lee los valores configurados; no usa códigos ficticios |
| Señal remota | Consola | `RemoteStreamEngine`, `StreamDTMFDetector` | Pautas locales → Consola | URL, volumen, play/stop y retorno preservados |
| Biblioteca de medios | Biblioteca | `_add_audio_files`, `_import_folder`, `_add_streaming_url`, `_filter_library` | Emisión → resumen; Biblioteca → gestión completa | La vista resumen se sincroniza con la tabla persistente de seis columnas |
| Pautas publicitarias | Biblioteca | `_new_pauta`, `_del_pauta` | Biblioteca → panel derecho | Edición y borrado preservados |
| Encoder/streaming | Control de audio | `StreamEncoder`, `StreamClient`, `_toggle_encoder`, `_config_encoder` | Emisión → estado; Dispositivos → controles completos | Estado desconectado independiente de la fuente al aire |
| Micrófono y ruteo | Control de audio | `_toggle_mic`, `AudioPassthrough` | Dispositivos | Fuente y volumen preservados |
| Persistencia | Inicio/cierre | `_load_*_from_disk`, `_save_*_to_disk` | Sin cambio | Se siguen usando los JSON existentes de `data/` |

## Estados sin simulación

- Sin una fuente confirmada, la cabecera muestra `SIN FUENTE CONFIRMADA`.
- Sin programación horaria real, el próximo evento muestra `Esperando tono` y no inventa una cuenta regresiva.
- Encoder, DTMF, dispositivos y respaldo parten en estado neutro o desconectado.
- Los medidores VU sólo reciben niveles emitidos por los motores de audio; se eliminó la animación aleatoria de reposo.
- Preescucha queda deshabilitada mientras no exista una ruta de monitoreo independiente confirmada.

## Validación visual

- Referencia principal: 1680 × 945 exterior (1680 × 910 de contenido en la captura sin decoración nativa).
- Escritorio compacto: 1366 × 768 exterior (1366 × 733 de contenido).
- En ambos tamaños se verificaron navegación lateral, cabecera operativa, dos columnas, pauta dominante, DTMF/salida a la derecha, biblioteca/registro inferiores y ausencia de desplazamiento horizontal global.
- Las vistas secundarias usan controles compactos y alineados: Pautas limita la consola y el reproductor al área operativa; Biblioteca separa medios y publicidad; DTMF agrupa dispositivos, parámetros, pruebas y estado; Dispositivos separa micrófono de encoder y expone el acceso al ruteo.
- Se comprobó cada una de las seis vistas a 1680 × 910 y la configuración DTMF a 1366 × 733, sin controles recortados.
- El cambio entre tema oscuro y claro reconstruye la interfaz con la paleta correspondiente y conserva biblioteca, pautas, playlist, secuencias DTMF, dispositivos seleccionados y estados operativos.
- En el tema claro se verificaron fondos, paneles, tablas, campos, texto y reloj con contraste legible; al volver al tema oscuro los datos permanecen intactos.
- Se validó la activación y desactivación del detector DTMF en ambos temas; los controladores heredados conservan sus receptores de estado y no generan errores de atributos ausentes.
- La biblioteca funciona como origen de arrastre múltiple; la pauta preparada y las pautas publicitarias aceptan audios soltados desde la biblioteca o desde Finder.
- Biblioteca, pauta preparada y pautas publicitarias se guardan automáticamente. Las escrituras JSON son atómicas para no dejar archivos parciales si la aplicación se interrumpe.
- Se probó el ciclo completo de añadir, editar horario, guardar, recargar, cambiar de tema y recorrer las seis vistas manteniendo los datos.
- La vista Emisión permite arrastrar desde su biblioteca inferior directamente a “Pauta local preparada”. El cambio de tema detiene el temporizador anterior antes de reconstruir la interfaz.
- El punto de entrada instala un manejador de excepciones de Qt: un error recuperable se registra y se muestra al operador sin abortar todo el proceso.
- El diálogo del encoder fue reorganizado a 840 × 690: servidor y codificación/captura en columnas, metadatos compactos al pie y acciones persistentes, validado sin superposiciones en tema claro y oscuro.
- La tarjeta de próxima desconexión mantiene título, estado y contador dentro de sus columnas a 1280 × 720. La telemetría RMS del detector ya no reemplaza el estado operativo visible.
- Se eliminaron los tooltips extensos sobre las tablas de arrastre —que tapaban el panel DTMF— y se sustituyeron por una indicación fija y discreta; los tooltips restantes tienen contraste explícito en ambos temas.
- El encoder trata el loopback como bus final de programa (cadena → pauta local → retorno), resuelve el dispositivo por nombre además de índice y muestra bytes realmente enviados.
- El cliente Icecast anuncia el MIME según el codec, conserva audio en cola durante la conexión y transmite desde un hilo dedicado. El protocolo se verificó contra un servidor Icecast local simulado con MP3.
