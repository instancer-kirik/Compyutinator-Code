import kotlinx.html.*
import kotlinx.html.stream.createHTML

fun main() {
    val html = createHTML().html {
        head {
            title("My Kotlin HTML Page")
            styleLink("/styles.css")
        }
        body {
            div(classes = "container") {
                h1 { +"Welcome to Kotlin HTML" }
                p { 
                    +"This is a paragraph with "
                    a(href = "https://kotlinlang.org") { +"a link" }
                }
                ul {
                    for (i in 1..3) {
                        li { +"Item $i" }
                    }
                }
            }
        }
    }
    println(html)
}
