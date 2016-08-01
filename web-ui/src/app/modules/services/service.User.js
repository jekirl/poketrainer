angular.module('Poketrainer.Service.User', ['ngResource', 'Poketrainer.Service.Config'])
    .factory('User', ['$resource', 'Config', function ($resource, Config) {
        return {
            query: function mockUserQuery(){
                return [
                    {
                        Id: 1,
                        Username: 'user-1'
                    },
                    {
                        Id: 2,
                        Username: 'user-2'
                    }
                ]
            }
        };
    }]);