angular.module('Poketrainer.Service.UserList', [])

    .factory('UserList', function UserListFactory() {
        var userList = [];
        var currentUser = '';

        var setUsers = function setUsers(users) {
            // show all users to unknown state until we receive a proper state
            for (var i = 0; i < users.length; i++) {
                users[i].status = 'unknown';
            }
            userList = users.sort(function (a, b) {
                return a.username.localeCompare(b.username);
            });
        };
        var userEventUpdate = function userEventUpdate(user) {
            for (var i = 0; i < userList.length; i++) {
                if (userList[i].username == user.username) {
                    userList[i].status = user.status;
                }
            }
            return userList;
        };
        var getUsers = function getUsers() {
            return userList;
        };
        var setCurrentUser = function setCurrentUser(username) {
            currentUser = username;
        };
        var getCurrentUser = function setCurrentUser() {
            for (var i = 0; i < userList.length; i++) {
                if (userList[i].username == currentUser) {
                    return userList[i];
                }
            }
            return {};
        };

        return {
            set: setUsers,
            update: userEventUpdate,
            get: getUsers,
            setCurrent: setCurrentUser,
            getCurrent: getCurrentUser
        };
    });