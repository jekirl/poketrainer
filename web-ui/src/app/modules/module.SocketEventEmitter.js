angular.module('Poketrainer.Module.SocketEventEmitter', ['Poketrainer.Service.Socket'])
    .run(function runSocketEmitter($rootScope, PokeSocket, SocketEvent){

        PokeSocket.forward(SocketEvent.UserStatus);

        PokeSocket.on(SocketEvent.Data, function getSocketPush(data){
            console.log("Got push data: ", data);

            $rootScope.$broadcast(data.event + ":" + data.action, data.data);
        });

        // Broadcast events using $rootScope.$broadcast([name], [data]);
    })

;