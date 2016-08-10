angular.module('Poketrainer.Module.SocketEventEmitter', ['Poketrainer.Service.Socket'])
    .run(function runSocketEmitter($rootScope, PokeSocket, SocketEvent){

        PokeSocket.forward(SocketEvent.UserList);
        PokeSocket.forward(SocketEvent.UserStatus);

        PokeSocket.on(SocketEvent.Data, function getSocketPush(data){
            console.log("Pushed: ", data);
        });

        // Broadcast events using $rootScope.$broadcast([name], [data]);
    })

;