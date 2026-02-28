// main.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: root
    visible: true
    width: 400
    height: 300
    title: qsTr("PyQt5与QML简单示例")

    // 定义一个信号，用于通知Python用户点击了按钮
    signal sendToPython(string message)

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 20

        Text {
            id: title
            text: "你好，来自QML！"
            font.pixelSize: 18
            Layout.alignment: Qt.AlignHCenter
        }

        Button {
            id: pyButton
            text: "点击我试试"
            Layout.alignment: Qt.AlignHCenter
            onClicked: {
                // 点击时发射信号，并传递一个字符串
                root.sendToPython("用户点击了QML中的按钮！")
            }
        }

        Label {
            id: messageFromPython
            text: "等待Python消息..."
            Layout.alignment: Qt.AlignHCenter
        }
    }
}