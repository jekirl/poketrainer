angular.module('Poketrainer.Service.Navigation', [])

    .factory('Navigation', function NavigationFactory() {
        var sidebarNav = {};
        var headerNav = [];

        var getSidebarMenu = function getSidebarMenu(state) {
            // Make sure we have a valid state before doing anything
            if (state === '') {
                return [];
            }

            var hasParent = (state.indexOf('.') >= 0);
            var hasMenu = angular.isDefined(sidebarNav[state]);

            // Do we have a menu for this state?
            // If we have no menu, and no parent,
            // simply return an empty array.
            if (!hasMenu && !hasParent) {
                return [];
            } else if (!hasMenu && hasParent) {
                // Since we do not have a menu for
                // this state, recurse up the tree
                // and get the menu of an ancestor
                var parent = (hasParent ? state.substring(0, state.lastIndexOf('.')) : '');
                return getSidebarMenu(parent);
            }

            var groups = angular.copy( sidebarNav[state] );

            // We got a menu, so simply return it!
            return groups.filter(function (menuGroup) {
                return (menuGroup.Items.length > 0);
            });
        };

        var indexOfGroup = function hasMenu(state, group) {
            var menu = sidebarNav[state];

            for (var i in menu) {
                var d = menu[i];

                if (d.Name == group) {
                    return i;
                }
            }

            return -1;
        };
        var indexOfLabel = function hasLabel(items, item) {

            for (var i in items) {
                var d = items[i];

                if (d.Label == item.Label) {
                    return i;
                }
            }

            return -1;
        };

        var registerSidebarMenu = function registerSidebarMenu(state, group, items) {
            if (!angular.isDefined(sidebarNav[state])) {
                sidebarNav[state] = [];
            }

            // Get the index of the current group (eg Orders)
            var groupIndex = indexOfGroup(state, group);

            // Check if the group already exists. If not, add it
            if (groupIndex == -1) {
                sidebarNav[state].push({
                    Name: group,
                    Items: items
                });
                return;
            }

            // Iterate through all items and add them
            // or replace with existing items.
            // The label has to be unique, hence if
            // an item is added with an existing label,
            // the existing label will be replaced.
            for (var i in items) {
                var item = items[i];

                // Get the index of the item label, if it
                // exists in the menu.
                var labelIndex = indexOfLabel(sidebarNav[state][groupIndex].Items, item);

                // If the label doesn't exist, simply add it.
                // Otherwise replace the existing item.
                if (labelIndex == -1) {
                    sidebarNav[state][groupIndex].Items.push(item);
                } else {
                    sidebarNav[state][groupIndex].Items[labelIndex] = item;
                }
            }


        };

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
            sidebar: {
                get: getSidebarMenu,
                register: registerSidebarMenu
            },
            primary: {
                get: getPrimaryMenu,
                register: registerPrimaryMenu
            }
        };
    });