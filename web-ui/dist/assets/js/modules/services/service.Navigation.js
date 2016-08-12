angular.module('Poketrainer.Service.Navigation', [])

    .factory('Navigation', function NavigationFactory() {
        var headerNav = [];

        var getPrimaryMenu = function getPrimaryMenu() {
            return headerNav.sort(function (a, b) {
                var priority = a.Priority - b.Priority;

                if (priority === 0) {
                    return a.Label.localeCompare(b.Label);
                }

                return priority;
            });
        };
        var registerPrimaryMenu = function registerPrimaryMenu(label, state, priority, icon, activeState) {
            if( typeof(icon) !== "string"){
                icon = "md md-chevron-right";
            }
            if( typeof(activeState) !== "string"){
                activeState = state;
            }

            if (typeof (priority) !== "number" || priority < 0) {
                priority = 10;
            }

            headerNav.push({
                Label: label,
                State: state,
                ActiveState: activeState,
                Priority: priority,
                Icon: icon
            });
        };

        return {
            primary: {
                get: getPrimaryMenu,
                register: registerPrimaryMenu
            }
        };
    });