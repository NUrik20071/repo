package com.mlregionswitcher.app

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.view.View
import android.widget.*
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private val bg = Color.rgb(16, 21, 34)
    private val panel = Color.rgb(28, 36, 55)
    private val accent = Color.rgb(121, 169, 255)
    private val white = Color.rgb(242, 245, 250)
    private val muted = Color.rgb(167, 179, 201)
    private val regions = listOf(
        "🇰🇿 Казахстан — KZ", "🇷🇺 Россия — RU", "🇺🇿 Узбекистан — UZ",
        "🇰🇬 Кыргызстан — KG", "🇧🇾 Беларусь — BY", "🇦🇲 Армения — AM",
        "🇦🇿 Азербайджан — AZ", "🇹🇯 Таджикистан — TJ"
    )
    private lateinit var selectedRegion: Spinner
    private lateinit var host: EditText
    private lateinit var port: EditText
    private lateinit var status: TextView
    private lateinit var ipText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
    }

    private fun buildUi() {
        val scroll = ScrollView(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(28), dp(20), dp(24))
            setBackgroundColor(bg)
        }
        scroll.addView(root)
        setContentView(scroll)

        root.addView(text("ML REGION SWITCHER", 12f, accent, true))
        root.addView(text("Выбор региона и проверка прокси", 25f, white, true).apply {
            setPadding(0, dp(8), 0, dp(6))
        })
        root.addView(text(
            "Прототип Android-приложения. Сам выбор страны не меняет игровой сервер.",
            14f, muted, false
        ))

        root.addView(section("РЕГИОН"))
        selectedRegion = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, regions)
        }
        root.addView(cardWrap(selectedRegion))

        root.addView(section("UPSTREAM ПРОКСИ"))
        root.addView(text("Адрес прокси", 14f, muted, false))
        host = EditText(this).apply {
            hint = "proxy.example.net"
            setSingleLine(true)
            setTextColor(white)
            setHintTextColor(muted)
            setPadding(dp(12), dp(8), dp(12), dp(8))
            setBackgroundColor(panel)
        }
        root.addView(host, lp(match, dp(52)))
        root.addView(text("Порт", 14f, muted, false).apply { setPadding(0, dp(10), 0, 0) })
        port = EditText(this).apply {
            hint = "1080"
            setText("1080")
            inputType = 2
            setSingleLine(true)
            setTextColor(white)
            setHintTextColor(muted)
            setPadding(dp(12), dp(8), dp(12), dp(8))
            setBackgroundColor(panel)
        }
        root.addView(port, lp(match, dp(52)))

        val testButton = Button(this).apply {
            text = "Проверить внешний IP"
            setTextColor(Color.BLACK)
            setBackgroundColor(accent)
            setOnClickListener { checkIp() }
        }
        root.addView(testButton, lp(match, dp(54)))

        root.addView(section("СОСТОЯНИЕ"))
        status = text("Прокси не проверен", 16f, white, true)
        root.addView(cardWrap(status))
        ipText = text("Внешний IP: —", 14f, muted, false)
        root.addView(cardWrap(ipText))

        root.addView(section("ВАЖНО ОБ ANDROID"))
        root.addView(text(
            "Обычное Android-приложение без VPNService и без root не может перехватывать и перенаправлять произвольный трафик другой игры. " +
            "Этот прототип пока проверяет прямой внешний IP устройства; поля прокси сохраняются только визуально и не означают, что игровой трафик идёт через прокси. " +
            "Для настоящей проверки прокси нужен поддерживаемый upstream-протокол и тестовый сервер. Даже работающий прокси не гарантирует выбор региона матчмейкинга Mobile Legends.",
            14f, muted, false
        ).apply {
            setPadding(dp(14), dp(14), dp(14), dp(14))
            setBackgroundColor(panel)
        })
    }

    private fun checkIp() {
        status.text = "Проверка…"
        ipText.text = "Внешний IP: загружается"
        thread {
            var result = "Не удалось получить IP"
            try {
                val conn = URL("https://api.ipify.org").openConnection() as HttpURLConnection
                conn.connectTimeout = 7000
                conn.readTimeout = 7000
                result = conn.inputStream.bufferedReader().use { it.readText().trim() }
                conn.disconnect()
            } catch (_: Exception) { }
            val finalResult = result
            runOnUiThread {
                status.text = if (finalResult.matches(Regex("\\d{1,3}(\\.\\d{1,3}){3}"))) {
                    "Интернет доступен — прямое соединение"
                } else "Проверка не удалась"
                ipText.text = "Внешний IP: $finalResult"
            }
        }
    }

    private fun section(s: String) = text(s, 12f, accent, true).apply {
        setPadding(0, dp(24), 0, dp(8))
    }

    private fun text(s: String, size: Float, color: Int, bold: Boolean) =
        TextView(this).apply {
            text = s
            textSize = size
            setTextColor(color)
            if (bold) setTypeface(null, android.graphics.Typeface.BOLD)
            setPadding(0, dp(4), 0, dp(4))
        }

    private fun cardWrap(v: View): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(8), dp(12), dp(8))
        setBackgroundColor(panel)
        addView(v)
        layoutParams = lp(match, wrap).apply { topMargin = dp(4) }
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()
    private val match get() = LinearLayout.LayoutParams.MATCH_PARENT
    private val wrap get() = LinearLayout.LayoutParams.WRAP_CONTENT
    private fun lp(w: Int, h: Int) = LinearLayout.LayoutParams(w, h)
}
