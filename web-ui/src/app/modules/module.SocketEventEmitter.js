angular.module('Poketrainer.Module.SocketEventEmitter', ['Poketrainer.Service.Socket'])
    .run(function runSocketEmitter($rootScope, User, PokeSocket, SocketEvent){

        PokeSocket.forward(SocketEvent.UserList);

        PokeSocket.on(SocketEvent.Data, function getSocketPush(data){
            console.log("Pushed: ", data);
        });

        // Broadcast events using $rootScope.$broadcast([name], [data]);
    })

;