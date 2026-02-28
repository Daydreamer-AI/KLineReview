import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    // 通过别名暴露属性，方便Python设置
    property alias message: displayText.text

    function setMessage(msg) {
        displayText.text = msg
    }

    Column {
        anchors.centerIn: parent
        spacing: 10

        Text {
            id: displayText
            text: "Hello from QML!"
            font.pixelSize: 16
        }

        Button {
            text: "Send to Python"
            onClicked: {
                // 点击按钮时，通过上下文属性调用Python方法
                policyFilterSettingBridge.receiveFromQml("Hello from QML Button!")
            }
        }
    }
}