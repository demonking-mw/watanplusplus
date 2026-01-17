import React, { createContext, useReducer } from "react";
import ACTIONS from "./actions";
import { type GameState } from "./utils/api.types";
import { isPlayersTurn } from "./utils/stateUtils";

export type CatanState = {
  gameState: GameState | null; // TODO
  freeRoadsAvailable: number;
  isBuildingRoad: boolean;
  isBuildingSettlement: boolean;
  isBuildingCity: boolean;
  isLeftDrawerOpen: boolean;
  isRightDrawerOpen: boolean;
  isPlayingMonopoly: boolean;
  isPlayingYearOfPlenty: boolean;
  isRoadBuilding: boolean;
  isMovingRobber: boolean;
  isFreeMovingRobber: boolean;
  isDeleting: boolean;
};
type ReducerAction = {
  type: keyof typeof ACTIONS;
  data?: any; // TODO find exact types
};

const initialState: CatanState = {
  gameState: null,
  // UI
  isBuildingRoad: false,
  isBuildingSettlement: false,
  isBuildingCity: false,
  isLeftDrawerOpen: false,
  isRightDrawerOpen: false,
  isPlayingMonopoly: false,
  isPlayingYearOfPlenty: false,
  isRoadBuilding: false,
  freeRoadsAvailable: 0,
  isMovingRobber: false,
  isFreeMovingRobber: false,
  isDeleting: false,
} as const;

const store = createContext<{
  state: CatanState;
  dispatch: React.ActionDispatch<[action: ReducerAction]>;
}>({ state: initialState, dispatch: () => {} });
const { Provider } = store;

const StateProvider = ({ children }: { children: React.ReactNode }) => {
  const [state, dispatch] = useReducer(
    (state: CatanState, action: ReducerAction) => {
      switch (action.type) {
        case ACTIONS.SET_LEFT_DRAWER_OPENED:
          return { ...state, isLeftDrawerOpen: action.data };
        case ACTIONS.SET_RIGHT_DRAWER_OPENED:
          return { ...state, isRightDrawerOpen: action.data };
        case ACTIONS.SET_GAME_STATE:
          // Check if there are still valid build actions available
          const newGameState = action.data;
          const isPlayerTurn = isPlayersTurn(newGameState);
          const hasBuildSettlementActions = isPlayerTurn && newGameState.current_playable_actions.some(
            (action: any) => action[1] === "BUILD_SETTLEMENT"
          );
          const hasBuildCityActions = isPlayerTurn && newGameState.current_playable_actions.some(
            (action: any) => action[1] === "BUILD_CITY"
          );
          const hasBuildRoadActions = isPlayerTurn && newGameState.current_playable_actions.some(
            (action: any) => action[1] === "BUILD_ROAD"
          );
          
          return {
            ...state,
            gameState: action.data,
            // Preserve building states only if it's still the player's turn and there are valid actions available
            // This allows users to keep clicking on the map without re-clicking "Buy"
            // But clears building states when turn changes or no valid actions remain
            isBuildingRoad: state.isBuildingRoad && hasBuildRoadActions,
            isBuildingSettlement: state.isBuildingSettlement && hasBuildSettlementActions,
            isBuildingCity: state.isBuildingCity && hasBuildCityActions,
            isRoadBuilding:
              state.isRoadBuilding && state.freeRoadsAvailable > 0,
            freeRoadsAvailable: state.isRoadBuilding
              ? state.freeRoadsAvailable - 1
              : 0,
            isPlayingMonopoly: false,
            isPlayingYearOfPlenty: false,
            isMovingRobber: false,
            isFreeMovingRobber: false,
            isDeleting: false,
          };
        case ACTIONS.TOGGLE_BUILDING_ROAD:
          return { ...state, isBuildingRoad: !state.isBuildingRoad };
        case ACTIONS.TOGGLE_BUILDING_SETTLEMENT:
          return { ...state, isBuildingSettlement: !state.isBuildingSettlement };
        case ACTIONS.TOGGLE_BUILDING_CITY:
          return { ...state, isBuildingCity: !state.isBuildingCity };
        case ACTIONS.SET_IS_BUILDING_SETTLEMENT:
          return { ...state, isBuildingSettlement: true };
        case ACTIONS.SET_IS_BUILDING_CITY:
          return { ...state, isBuildingCity: true };
        case ACTIONS.CANCEL_BUILDING_ROAD:
          return { ...state, isBuildingRoad: false };
        case ACTIONS.CANCEL_BUILDING_SETTLEMENT:
          return { ...state, isBuildingSettlement: false };
        case ACTIONS.CANCEL_BUILDING_CITY:
          return { ...state, isBuildingCity: false };
        case ACTIONS.SET_IS_PLAYING_MONOPOLY:
          return { ...state, isPlayingMonopoly: true };
        case ACTIONS.CANCEL_MONOPOLY:
          return { ...state, isPlayingMonopoly: false };
        case ACTIONS.SET_IS_PLAYING_YEAR_OF_PLENTY:
          return { ...state, isPlayingYearOfPlenty: true };
        case ACTIONS.CANCEL_YEAR_OF_PLENTY:
          return { ...state, isPlayingYearOfPlenty: false };
        case ACTIONS.PLAY_ROAD_BUILDING:
          return {
            ...state,
            isRoadBuilding: true,
            freeRoadsAvailable: 2,
          };
        case ACTIONS.SET_IS_MOVING_ROBBER:
          return { ...state, isMovingRobber: true };
        case ACTIONS.SET_IS_FREE_MOVING_ROBBER:
          return { ...state, isFreeMovingRobber: !state.isFreeMovingRobber };
        case ACTIONS.SET_IS_DELETING:
          return { ...state, isDeleting: !state.isDeleting };
        default:
          throw new Error("Unknown Reducer Action: " + action.type);
      }
    },
    initialState
  );

  return <Provider value={{ state, dispatch }}>{children}</Provider>;
};

export { store, StateProvider };
