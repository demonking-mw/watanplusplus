import { useCallback, useContext, useEffect, useState } from "react";
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import memoize from "fast-memoize";
import { useMediaQuery, useTheme } from "@mui/material";

import useWindowSize from "../utils/useWindowSize";

import "./Board.scss";
import { store } from "../store";
import { isPlayersTurn } from "../utils/stateUtils";
import { postAction } from "../utils/apiClient";
import type { CatanState } from "../store";
import { useParams } from "react-router";
import ACTIONS from "../actions";
import Board from "./Board";
import { toEdgeId } from "./Edge";
import type { GameAction, TileCoordinate } from "../utils/api.types";

/**
 * Returns object representing actions to be taken if click on node.
 * @returns {3 => ["BLUE", "BUILD_CITY", 3], ...}
 */
function buildNodeActions(state: CatanState) {
  if (!state.gameState)
    throw new Error("GameState is not ready!");

  if (!isPlayersTurn(state.gameState)) {
    return {};
  }

  const nodeActions: Record<number, GameAction> = {};
  const buildInitialSettlementActions = state.gameState.is_initial_build_phase
    ? state.gameState.current_playable_actions.filter(
        (action) => action[1] === "BUILD_SETTLEMENT"
      )
    : [];
  const inInitialBuildPhase = state.gameState.is_initial_build_phase;
  if (inInitialBuildPhase) {
    buildInitialSettlementActions.forEach((action) => {
      nodeActions[action[2]] = action;
    });
  } else if (state.isBuildingSettlement) {
    state.gameState.current_playable_actions
      .filter((action) => action[1] === "BUILD_SETTLEMENT")
      .forEach((action) => {
        nodeActions[action[2]] = action;
      });
  } else if (state.isBuildingCity) {
    state.gameState.current_playable_actions
      .filter((action) => action[1] === "BUILD_CITY")
      .forEach((action) => {
        nodeActions[action[2]] = action;
      });
  } else if (state.isDeleting) {
    // In delete mode, show all buildings that belong to the current player
    const currentColor = state.gameState.current_color;
    // nodes is an object, not an array, so use Object.values
    Object.values(state.gameState.nodes).forEach((node) => {
      if (node.building && node.color === currentColor) {
        // Create delete action based on building type
        if (node.building === "SETTLEMENT") {
          nodeActions[node.id] = [currentColor, "DELETE_SETTLEMENT", node.id];
        } else if (node.building === "CITY") {
          nodeActions[node.id] = [currentColor, "DELETE_CITY", node.id];
        }
      }
    });
  }
  return nodeActions;
}

function buildEdgeActions(state: CatanState) {
  if (!state.gameState)
    throw new Error("GameState is not ready!");
  if (!isPlayersTurn(state.gameState)) {
    return {};
  }

  const edgeActions: Record<`${number},${number}`, GameAction> = {};
  const buildInitialRoadActions = state.gameState.is_initial_build_phase
    ? state.gameState.current_playable_actions.filter(
        (action) => action[1] === "BUILD_ROAD"
      )
    : [];
  const inInitialBuildPhase = state.gameState.is_initial_build_phase;
  if (inInitialBuildPhase) {
    buildInitialRoadActions.forEach((action) => {
      edgeActions[`${action[2][0]},${action[2][1]}`] = action;
      console.log(Object.keys(edgeActions), action);
    });
  } else if (state.isBuildingRoad || state.isRoadBuilding) {
    state.gameState.current_playable_actions
      .filter((action) => action[1] === "BUILD_ROAD")
      .forEach((action) => {
        edgeActions[`${action[2][0]},${action[2][1]}`] = action;
      });
  } else if (state.isDeleting) {
    // In delete mode, show all roads that belong to the current player
    const currentColor = state.gameState.current_color;
    // edges is an array, so forEach should work
    const edgesArray = Array.isArray(state.gameState.edges) 
      ? state.gameState.edges 
      : Object.values(state.gameState.edges || {});
    edgesArray.forEach((edge) => {
      if (edge.color === currentColor) {
        // Use toEdgeId to ensure consistent format matching what Edge component expects
        const edgeId = toEdgeId(edge.id);
        edgeActions[edgeId] = [currentColor, "DELETE_ROAD", edge.id];
      }
    });
    console.log("Delete mode - edgeActions:", Object.keys(edgeActions), "currentColor:", currentColor, "totalEdges:", edgesArray.length, "playerEdges:", edgesArray.filter(e => e.color === currentColor).length);
  }
  return edgeActions;
}

type ZoomableBoardProps = {
  replayMode: boolean;
}

export default function ZoomableBoard({ replayMode }: ZoomableBoardProps) {
  const { gameId } = useParams();
  const { state, dispatch } = useContext(store);
  const { width, height } = useWindowSize();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.up("md"));
  const [show, setShow] = useState(false);
  const gameState = state.gameState
  if (!gameState)
    throw new Error("GameState is not ready!");
  if (!gameId)
    throw new Error("expecting gameId in URL");

  // TODO: Move these up to GameScreen and let Zoomable be presentational component
  // https://stackoverflow.com/questions/61255053/react-usecallback-with-parameter
  const buildOnNodeClick = useCallback(
    memoize((id, action) => async () => {
      console.log("Clicked Node ", id, action);
      if (action) {
        const gameState = await postAction(gameId, action);
        dispatch({ type: ACTIONS.SET_GAME_STATE, data: gameState });
        // Turn off delete mode after deleting
        if (state.isDeleting && (action[1] === "DELETE_SETTLEMENT" || action[1] === "DELETE_CITY")) {
          dispatch({ type: ACTIONS.SET_IS_DELETING });
        }
      }
    }),
    [state.isDeleting, gameId, dispatch]
  );
  const buildOnEdgeClick = useCallback(
    memoize((id, action) => async () => {
      console.log("Clicked Edge ", id, action);
      if (action) {
        const gameState = await postAction(gameId, action);
        dispatch({ type: ACTIONS.SET_GAME_STATE, data: gameState });
        // Turn off delete mode after deleting
        if (state.isDeleting && (action[1] === "DELETE_ROAD")) {
          dispatch({ type: ACTIONS.SET_IS_DELETING });
        }
      }
    }),
    [state.isDeleting, gameId, dispatch]
  );
  const handleTileClick = useCallback(
    memoize((coordinate: TileCoordinate) => {
      console.log("Clicked Tile ", coordinate);
      if (state.isFreeMovingRobber) {
        // Free rob mode: move robber to any tile without game logic restrictions
        const humanColor = !gameState.bot_colors.includes(gameState.current_color) 
          ? gameState.current_color 
          : gameState.colors.find(color => !gameState.bot_colors.includes(color)) || gameState.colors[0];
        const freeRobAction: GameAction = [
          humanColor,
          "MOVE_ROBBER",
          [coordinate, null] // null means don't steal from anyone
        ];
        postAction(gameId, freeRobAction).then((updatedGameState) => {
          dispatch({ type: ACTIONS.SET_GAME_STATE, data: updatedGameState });
          dispatch({ type: ACTIONS.SET_IS_FREE_MOVING_ROBBER }); // Turn off free rob mode after moving
        }).catch((error) => {
          console.error("Error moving robber:", error);
        });
      } else if (state.isMovingRobber) {
        // Normal rob mode: Find the "MOVE_ROBBER" action in current_playable_actions that
        // corresponds to the tile coordinate selected by the user
        const matchingAction = gameState.current_playable_actions.find(
          ([, action_type, [action_coordinate, ,]]) =>
            action_type === "MOVE_ROBBER" &&
            action_coordinate.every((val: number, index: number) => val === coordinate[index])
        );
        if (matchingAction) {
          postAction(gameId, matchingAction).then((updatedGameState) => {
            dispatch({ type: ACTIONS.SET_GAME_STATE, data: updatedGameState });
          });
        }
      }
    }),
    [state.isMovingRobber, state.isFreeMovingRobber, state.isDeleting, gameState, gameId, dispatch]
  );

  const nodeActions = replayMode ? {} : buildNodeActions(state);
  const edgeActions = replayMode ? {} : buildEdgeActions(state);

  useEffect(() => {
    setTimeout(() => {
      setShow(true);
    }, 300);
  }, []);

  if (!width || !height) return;

  return (
    <TransformWrapper>
      <div className="board-container">
        <TransformComponent>
          <Board
            width={width}
            height={height}
            buildOnNodeClick={buildOnNodeClick}
            buildOnEdgeClick={buildOnEdgeClick}
            handleTileClick={handleTileClick}
            nodeActions={nodeActions}
            edgeActions={edgeActions}
            replayMode={replayMode}
            show={show}
            gameState={gameState}
            isMobile={isMobile}
            isMovingRobber={state.isMovingRobber}
            isFreeMovingRobber={state.isFreeMovingRobber}
            isDeleting={state.isDeleting}
          />
        </TransformComponent>
      </div>
    </TransformWrapper>
  );
}
