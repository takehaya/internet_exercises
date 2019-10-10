const server = require("ws").Server;
const s = new server({ port: 5001 });

var connects = []

s.on("connection", ws => {
    connects.push(ws); // 配列にソケットを格納
    ws.on("message", message => {
        console.log("Received: " + message);
        broadcast(message, ws);
    });
    ws.on("close", message => {
        // 接続切れのソケットを配列から除外
        connects = connects.filter(function (conn, i) {
            return (conn === ws) ? false : true;
        });
    });
});

function broadcast (message,sc) {
    connects.forEach(function (socket, i) {
        if (sc !== socket){
            socket.send(message);
        }
    });
}
