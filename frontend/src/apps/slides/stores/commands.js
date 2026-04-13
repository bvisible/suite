import { findElement } from '@/stores/element'

export const editElementCommand = ({ slideId, elementId, property, oldValue, newValue }) => {
	return {
		slideId,
		debug: `Edit ${property} of element ${elementId} on slide ${slideId} to ${newValue}`,
		execute(state) {
			findElement(state, slideId, elementId)[property] = newValue
		},
		undo(state) {
			findElement(state, slideId, elementId)[property] = oldValue
		},
	}
}
