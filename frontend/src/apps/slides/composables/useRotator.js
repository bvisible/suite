import { ref } from 'vue'

export const useRotator = () => {
	const isRotating = ref(false)
	const rotationDelta = ref(0)

	const startRotate = (e) => {}

	return { isRotating, rotationDelta, startRotate }
}
